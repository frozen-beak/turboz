import os
import math
import base64

from pydantic import BaseModel

_STOP_WORDS = set(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "he",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "that",
        "the",
        "to",
        "was",
        "were",
        "will",
        "with",
    ]
)


class SearchEngine:

    def __init__(self):
        self.documents, self.filenames = self.read_documents("./cars")
        self.total_docs = len(self.documents)
        self.inverted_index = self.build_inverted_index(self.documents)
        self.idf = self.compute_idf(self.inverted_index, self.total_docs)
        self.tf_idf_matrix = self.compute_tf_idf(self.documents, self.idf)

    def decode_filename(self, encoded_filename):
        encoded_str = encoded_filename.split("'")[1]
        decoded_bytes = base64.b64decode(encoded_str)
        link = decoded_bytes.decode("utf-8")

        return link

    def read_documents(self, directory):
        """
        Read all text files from the given directory.

        Parameters:
            directory (str): Path to the directory containing documents.

        Returns:
            list: List of document texts.
        """
        documents = []
        filenames = []

        for filename in os.listdir(directory):
            if filename.endswith(".txt"):
                filepath = os.path.join(directory, filename)

                with open(filepath, "r", encoding="utf-8") as file:
                    text = file.read()
                    documents.append(text)
                    filenames.append(filename)

        return documents, filenames

    def preprocess(self, text):
        """
        Preprocess the text by converting to lowercase, removing punctuation, and removing stop words.

        Parameters:
            text (str): Input text to preprocess.

        Returns:
            list: List of preprocessed tokens.
        """
        text = text.lower()
        translator = str.maketrans("", "", "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")

        text = text.translate(translator)
        tokens = text.split()

        tokens = [word for word in tokens if word not in _STOP_WORDS]

        return tokens

    def build_inverted_index(self, documents):
        """
        Build an inverted index mapping each word to the list of documents it appears in.

        Parameters:
            documents (list): List of document texts.

        Returns:
            dict: Inverted index.
        """
        inverted_index = {}

        for doc_idx, doc in enumerate(documents):
            tokens = self.preprocess(doc)
            unique_tokens = set(tokens)

            for token in unique_tokens:
                if token not in inverted_index:
                    inverted_index[token] = []
                inverted_index[token].append(doc_idx)

        return inverted_index

    def compute_idf(self, inverted_index, total_docs):
        """
        Compute the Inverse Document Frequency (IDF) for each term in the inverted index.

        Parameters:
            inverted_index (dict): Mapping from words to list of document indices.
            total_docs (int): Total number of documents.

        Returns:
            dict: IDF scores for each term.
        """
        idf_scores = {}

        for word, doc_list in inverted_index.items():
            df = len(doc_list)
            idf = math.log(total_docs / (1 + df))
            idf_scores[word] = idf

        return idf_scores

    def compute_tf(self, document):
        """
        Compute the Term Frequency (TF) for a document.

        Parameters:
            document (str): Document text.

        Returns:
            dict: TF scores for each term in the document.
        """
        tokens = self.preprocess(document)
        doc_length = len(tokens)
        tf_scores = {}

        for token in tokens:
            tf_scores[token] = tf_scores.get(token, 0.0) + 1.0

        for word in tf_scores:
            tf_scores[word] /= doc_length

        return tf_scores

    def compute_tf_idf(self, documents, idf):
        """
        Compute the TF-IDF representation for all documents.

        Parameters:
            documents (list): List of document texts.
            idf (dict): IDF scores for each term.

        Returns:
            list: List of dictionaries, each containing TF-IDF scores for a document.
        """
        tf_idf_matrix = []

        for doc in documents:
            tf = self.compute_tf(doc)
            tf_idf = {word: tf.get(word, 0.0) * idf.get(word, 0.0) for word in idf}
            tf_idf_matrix.append(tf_idf)

        return tf_idf_matrix

    def compute_query_tf_idf(self, query, idf):
        """
        Compute the TF-IDF vector for the query.

        Parameters:
            query (str): Query text.
            idf (dict): IDF scores for each term.

        Returns:
            dict: TF-IDF scores for the query.
        """
        tokens = self.preprocess(query)
        query_length = len(tokens)
        tf = {}

        for token in tokens:
            tf[token] = tf.get(token, 0.0) + 1.0

        for word in tf:
            tf[word] /= query_length
        query_tf_idf = {word: tf.get(word, 0.0) * idf.get(word, 0.0) for word in idf}

        return query_tf_idf

    def cosine_similarity(self, vector1, vector2):
        """
        Compute the cosine similarity between two sparse vectors.

        Parameters:
            vector1 (dict): First vector.
            vector2 (dict): Second vector.

        Returns:
            float: Cosine similarity score.
        """
        common_words = set(vector1.keys()) & set(vector2.keys())
        dot_product = sum(vector1[word] * vector2[word] for word in common_words)

        norm1 = math.sqrt(sum(vector1[word] ** 2 for word in vector1))
        norm2 = math.sqrt(sum(vector2[word] ** 2 for word in vector2))

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def search(self, query, idf, tf_idf_matrix, top_n=5):
        """
        Search for documents similar to the query.

        Parameters:
            query (str): Query text.
            documents (list): List of document texts.
            idf (dict): IDF scores for each term.
            tf_idf_matrix (list): List of dictionaries with TF-IDF scores for each document.
            top_n (int): Number of top documents to return.

        Returns:
            list: List of tuples containing document index and similarity score.
        """
        query_tf_idf = self.compute_query_tf_idf(query, idf)
        similarities = []

        for idx, doc_tf_idf in enumerate(tf_idf_matrix):
            sim = self.cosine_similarity(query_tf_idf, doc_tf_idf)
            similarities.append((idx, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_n]

    def perform_search(self, query: str):
        results = self.search(query, self.idf, self.tf_idf_matrix, top_n=5)

        final_results = []

        for idx, score in results:
            filename = self.filenames[idx]
            link = self.decode_filename(filename)
            doc_text = self.documents[idx]

            name = self.extract_car_name(link)
            desc, specs = self.split_document(doc_text)
            spec_dict = self.parse_specifications(specs)

            result = _CarResult(
                name=name,
                link=link,
                desc=desc,
                engine=spec_dict.get("engine", "-"),
                weight=spec_dict.get("weight", "-"),
                power=spec_dict.get("power", "-"),
                zero_to_sixty=spec_dict.get("0-62", "-"),
                torque=spec_dict.get("torque", "-"),
                top_speed=spec_dict.get("top speed", "-"),
                score=score,
            )

            final_results.append(result)

        return final_results

    def decode_filename(self, encoded_filename):
        encoded_str = encoded_filename.split("'")[1]
        decoded_bytes = base64.b64decode(encoded_str)

        link = decoded_bytes.decode("utf-8")

        return link

    def extract_car_name(self, link):
        path = link.strip("/").split("/")[-1]
        camel_case_parts = [
            part.capitalize() if not part.isdigit() else part
            for part in path.split("-")
        ]
        name = " ".join(camel_case_parts)

        return name

    def split_document(self, doc_text):
        parts = doc_text.split("\n\n", 1)

        desc = parts[0] if len(parts) >= 1 else ""
        specs = parts[1] if len(parts) >= 2 else ""

        return desc, specs

    def parse_specifications(self, specs_text):
        spec_dict = {}
        lines = specs_text.strip().split("\n")

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()

                value = value.strip()
                spec_dict[key] = value

        return spec_dict


class _CarResult(BaseModel):
    name: str
    link: str
    desc: str
    engine: str
    weight: str
    power: str
    zero_to_sixty: str
    torque: str
    top_speed: str
    score: float
