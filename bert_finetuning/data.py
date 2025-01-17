## dataset source: https://www.kaggle.com/team-ai/spam-text-message-classification
import pandas as pd
import torch
from keras.preprocessing.sequence import pad_sequences
from sklearn.model_selection import train_test_split
from transformers import BertTokenizer, BertConfig
from tqdm import tqdm
import logging
import re

## setting the threshold of logger to INFO
logging.basicConfig(filename="data_loader.log", level=logging.INFO)

## creating an object
logger = logging.getLogger()


class GermanData:
    def __init__(
        self,
        data_path,
        model_name,
        separator=",",
        max_sequence_length=512,
        do_cleansing=True,
    ):
        """
        Load dataset and bert tokenizer
        """
        self.do_cleansing = do_cleansing
        self.clean_chars = re.compile(r"[^A-Za-züöäÖÜÄß ]", re.MULTILINE)
        self.clean_http_urls = re.compile(r"https*\\S+", re.MULTILINE)
        self.clean_at_mentions = re.compile(r"@\\S+", re.MULTILINE)
        ## load data into memory
        self.train_df = pd.read_csv(data_path["train"], sep=separator)
        self.dev_df = pd.read_csv(data_path["dev"], sep=separator)
        self.test_df = pd.read_csv(data_path["test"], sep=separator)
        ## set max sequence length for model
        self.max_sequence_length = max_sequence_length
        ## get bert tokenizer
        self.tokenizer = BertTokenizer.from_pretrained(model_name, do_lower_case=True)

    def train_val_test_split(self):
        """
        Separate out labels and texts
        """
        train_texts = self.train_df["text"].values
        train_labels = self.train_df["label"].values
        val_texts = self.dev_df["text"].values
        val_labels = self.dev_df["label"].values
        test_texts = self.test_df["text"].values
        test_labels = self.test_df["label"].values

        return train_texts, val_texts, test_texts, train_labels, val_labels, test_labels

    def replace_numbers(self, text: str) -> str:
        return (
            text.replace("0", " null")
            .replace("1", " eins")
            .replace("2", " zwei")
            .replace("3", " drei")
            .replace("4", " vier")
            .replace("5", " fünf")
            .replace("6", " sechs")
            .replace("7", " sieben")
            .replace("8", " acht")
            .replace("9", " neun")
        )

    def clean_text(self, text: str) -> str:
        text = text.replace("\n", " ")
        text = self.clean_http_urls.sub("", text)
        text = self.clean_at_mentions.sub("", text)
        text = self.replace_numbers(text)
        text = self.clean_chars.sub("", text)  # use only text chars
        text = " ".join(
            text.split()
        )  # substitute multiple whitespace with single whitespace
        text = text.strip().lower()
        return text

    def preprocess(self, texts):
        """
        Clean sequences and add bert token (CLS and SEP) tokens to each sequence pre-tokenization
        """
        if self.do_cleansing:
            ## perform cleansing on text
            texts = [self.clean_text(text) for text in texts]
        ## separate labels and texts before preprocessing
        # Adding CLS and SEP tokens at the beginning and end of each sequence for BERT
        texts_processed = ["[CLS] " + str(sequence) + " [SEP]" for sequence in texts]
        return texts_processed

    def tokenize(self, texts):
        """
        Use bert tokenizer to tokenize each sequence and post-process
        by padding or truncating to a fixed length
        """
        ## tokenize sequence
        tokenized_texts = [self.tokenizer.tokenize(text) for text in tqdm(texts)]

        ## convert tokens to ids
        print("convert tokens to ids")
        text_ids = [
            self.tokenizer.convert_tokens_to_ids(x) for x in tqdm(tokenized_texts)
        ]

        ## pad our text tokens for each sequence
        print("pad our text tokens for each sequence")
        text_ids_post_processed = pad_sequences(
            text_ids,
            maxlen=self.max_sequence_length,
            dtype="long",
            truncating="post",
            padding="post",
        )
        return text_ids_post_processed

    def create_attention_mask(self, text_ids):
        """
        Add attention mask for padding tokens
        """
        attention_masks = []
        # create a mask of 1s for each token followed by 0s for padding
        for seq in tqdm(text_ids):
            seq_mask = [float(i > 0) for i in seq]
            attention_masks.append(seq_mask)
        return attention_masks

    def process_texts(self):
        """
        Apply preprocessing and tokenization pipeline of texts
        """
        ## perform the split
        (
            train_texts,
            val_texts,
            test_texts,
            train_labels,
            val_labels,
            test_labels,
        ) = self.train_val_test_split()

        print("preprocessing texts")
        ## preprocess train, val, test texts
        train_texts_processed = self.preprocess(train_texts)
        val_texts_processed = self.preprocess(val_texts)
        test_texts_processed = self.preprocess(test_texts)

        del train_texts
        del val_texts
        del test_texts

        ## preprocess train, val, test texts
        print("tokenizing train texts")
        train_ids = self.tokenize(train_texts_processed)
        print("tokenizing val texts")
        val_ids = self.tokenize(val_texts_processed)
        print("tokenizing test texts")
        test_ids = self.tokenize(test_texts_processed)

        del train_texts_processed
        del val_texts_processed
        del test_texts_processed

        del self.train_df
        del self.dev_df
        del self.test_df

        ## create masks for train, val, test texts
        print("creating train attention masks for texts")
        train_masks = self.create_attention_mask(train_ids)
        print("creating val attention masks for texts")
        val_masks = self.create_attention_mask(val_ids)
        print("creating test attention masks for texts")
        test_masks = self.create_attention_mask(test_ids)
        return (
            train_ids,
            val_ids,
            test_ids,
            train_masks,
            val_masks,
            test_masks,
            train_labels,
            val_labels,
            test_labels,
        )

    def text_to_tensors(self):
        """
        Converting all the data into torch tensors
        """
        (
            train_ids,
            val_ids,
            test_ids,
            train_masks,
            val_masks,
            test_masks,
            train_labels,
            val_labels,
            test_labels,
        ) = self.process_texts()

        print("converting all variables to tensors")
        ## convert inputs, masks and labels to torch tensors
        self.train_inputs = torch.tensor(train_ids)
        self.train_labels = torch.tensor(train_labels)
        self.train_masks = torch.tensor(train_masks)

        self.validation_inputs = torch.tensor(val_ids)
        self.validation_labels = torch.tensor(val_labels)
        self.validation_masks = torch.tensor(val_masks)

        self.test_inputs = torch.tensor(test_ids)
        self.test_labels = torch.tensor(test_labels)
        self.test_masks = torch.tensor(test_masks)


"""
** FOR DEBUGGING **

if __name__ == "__main__":
    germeval_data_paths = {
        "train": "./datasets/hasoc_dataset/hasoc_german_train.csv",
        "dev": "./datasets/hasoc_dataset/hasoc_german_validation.csv",
        "test": "./datasets/hasoc_dataset/hasoc_german_test.csv",
    }

    hasoc_german_data_paths = {
        "train": "./datasets/hasoc_dataset/hasoc_german_train.csv",
        "dev": "./datasets/hasoc_dataset/hasoc_german_validation.csv",
        "test": "./datasets/hasoc_dataset/hasoc_german_test.csv",
    }

    GermanData(
        hasoc_german_data_paths,
    ).text_to_tensors()
"""
