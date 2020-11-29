import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# !pip install -U tf-hub-nightly
# import tensorflow_hub as hub
import tensorflow as tf

from tensorflow.keras import layers, Input, Model

# 사전 훈련된 모델 MobileNet V2에서 기본 모델을 생성합니다.
IMG_SIZE = 224                      # VGG19
IMG_SHAPE = (IMG_SIZE, IMG_SIZE, 3)

base_model = tf.keras.applications.ResNet152V2(input_shape=IMG_SHAPE,
                                               include_top=False,
                                               weights='imagenet')

base_model.summary()

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, Dense, MaxPooling2D, Dropout, Flatten,GlobalAveragePooling2D
    
# The last 15 layers fine tune
for layer in base_model.layers[:-15]:
    layer.trainable = False

x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Flatten()(x)
x = Dense(units=512, activation='relu')(x)
x = Dropout(0.3)(x)
x = Dense(units=512, activation='relu')(x)
x = Dropout(0.3)(x)
output  = Dense(units=10, activation='softmax')(x)
model = Model(base_model.input, output)


model.summary()

# import sys
# sys.exit()

# Load the CIFAR-10 dataset
cifar10 = tf.keras.datasets.cifar10

# load dataset
(X_train, Y_train) , (X_test, Y_test) = cifar10.load_data()

import numpy as np
import cv2

import matplotlib.pyplot as plt

NUM_CLASSES = 10

# Onehot encode labels

Y_train = tf.keras.utils.to_categorical(Y_train, NUM_CLASSES)
Y_test = tf.keras.utils.to_categorical(Y_test, NUM_CLASSES)

model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["categorical_accuracy"])

# returns batch_size random samples from either training set or validation set
# resizes each image to (224, 244, 3), the native input size for VGG19
def getBatch(batch_size, train_or_val='train'):
    x_batch = []
    y_batch = []
    if train_or_val == 'train':
        idx = np.random.randint(0, len(X_train), (batch_size))

        for i in idx:
            img = cv2.resize(X_train[i], (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_CUBIC)
            x_batch.append(img)
            y_batch.append(Y_train[i])
    elif train_or_val == 'val':
        idx = np.random.randint(0, len(X_test), (batch_size))

        for i in idx:
            img = cv2.resize(X_test[i], (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_CUBIC)
            x_batch.append(img)
            y_batch.append(Y_test[i]) 
    else:
        print("error, please specify train or val")

    x_batch = np.array(x_batch)
    y_batch = np.array(y_batch)
    return x_batch, y_batch

EPOCHS = 10
# BATCH_SIZE = 250
# VAL_SIZE = 500
BATCH_SIZE = 50
VAL_SIZE = 50
STEPS = 50

for e in range(EPOCHS):
    train_loss = 0
    train_acc = 0

    for s in range(STEPS):
        x_batch, y_batch = getBatch(BATCH_SIZE, "train")
        out = model.train_on_batch(x_batch, y_batch)
        train_loss += out[0]
        train_acc += out[1]

    print(f"Epoch: {e+1}\nTraining Loss = {train_loss / STEPS}\tTraining Acc = {train_acc / STEPS}")

    x_v, y_v = getBatch(VAL_SIZE, "val")
    eval = model.evaluate(x_v, y_v)
    print(f"Validation loss: {eval[0]}\tValidation Acc: {eval[1]}\n")

# Sample outputs from validation set
LABELS_LIST = "airplane automobile bird cat deer dog frog horse ship truck".split(" ")

import matplotlib.pyplot as plt

x_v, y_v = getBatch(10, "val")

for i in range(10):
    import numpy as np
    plt.imshow(x_v[i])
    plt.show()
    print("pred: " + LABELS_LIST[np.argmax(model.predict(x_v[i:i+1]))])
    print("acct: " + LABELS_LIST[np.argmax(y_v[i])])