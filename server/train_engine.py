import json
import numpy as np
import pickle
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Embedding, LSTM, SpatialDropout1D, Bidirectional, Dropout, GlobalMaxPooling1D, GlobalAveragePooling1D, concatenate
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.regularizers import l2
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split 
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from utils.text_preprocessing import text_normalize

VOCAB_SIZE = 8000
EMBEDDING_DIM = 128
MAX_LEN = 30
EPOCHS = 300     
BATCH_SIZE = 32

with open('data/intents.json') as file:
    data = json.load(file)

factory = StemmerFactory()
stemmer = factory.create_stemmer()

training_sentences = []
training_labels = []
labels = []

for intent in data['intents']:
    for pattern in intent['patterns']:
        clean_pattern = text_normalize(pattern)
        clean_pattern = stemmer.stem(clean_pattern)
        training_sentences.append(clean_pattern)
        training_labels.append(intent['tag'])
    if intent['tag'] not in labels:
        labels.append(intent['tag'])

lbl_encoder = LabelEncoder()
lbl_encoder.fit(training_labels)
training_labels_encoded = lbl_encoder.transform(training_labels)

tokenizer = Tokenizer(num_words=VOCAB_SIZE, oov_token="<OOV>")
tokenizer.fit_on_texts(training_sentences)
sequences = tokenizer.texts_to_sequences(training_sentences)
padded_sequences = pad_sequences(sequences, truncating='post', maxlen=MAX_LEN)

input_train, input_val, label_train, label_val = train_test_split(
    padded_sequences, 
    training_labels_encoded, 
    test_size=0.2, 
    random_state=42, 
    stratify=training_labels_encoded 
)

input_layer = Input(shape=(MAX_LEN,))
x = Embedding(VOCAB_SIZE, EMBEDDING_DIM)(input_layer)
x = SpatialDropout1D(0.4)(x)
x = Bidirectional(LSTM(64, return_sequences=True))(x)

avg_pool = GlobalAveragePooling1D()(x)
max_pool = GlobalMaxPooling1D()(x)
merged = concatenate([avg_pool, max_pool])

x = Dense(128, activation='relu')(merged)
x = Dropout(0.5)(x)
output_layer = Dense(len(labels), activation='softmax')(x)

model = Model(inputs=input_layer, outputs=output_layer)
model.compile(loss='sparse_categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

early_stop = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=1)
reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, min_lr=1e-6, verbose=1)

history = model.fit(
    input_train, label_train, 
    epochs=EPOCHS, 
    batch_size=BATCH_SIZE,
    validation_data=(input_val, label_val), 
    callbacks=[early_stop, reduce_lr],
    verbose=1
)

model.save("models/chatbot_model.h5")
with open('models/tokenizer.pickle', 'wb') as handle:
    pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
with open('models/label_encoder.pickle', 'wb') as ecn_file:
    pickle.dump(lbl_encoder, ecn_file, protocol=pickle.HIGHEST_PROTOCOL)

acc = history.history['accuracy']
val_acc = history.history['val_accuracy']
loss = history.history['loss']
val_loss = history.history['val_loss']
epochs_range = range(len(acc))

plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(epochs_range, acc, label='Training Accuracy')
plt.plot(epochs_range, val_acc, label='Validation Accuracy')
plt.legend(loc='lower right')
plt.title('Training and Validation Accuracy')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')

plt.subplot(1, 2, 2)
plt.plot(epochs_range, loss, label='Training Loss')
plt.plot(epochs_range, val_loss, label='Validation Loss')
plt.legend(loc='upper right')
plt.title('Training and Validation Loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')

plt.tight_layout()
plt.savefig('grafik_evaluasi_model.png')
plt.show()