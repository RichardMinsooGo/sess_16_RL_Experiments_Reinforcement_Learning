#Importing Libraries
import numpy as np
import cv2

import matplotlib.pyplot as plt
import time

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf

from tensorflow.keras import layers, Input, Model
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten, Dropout

#Define network
IMG_SIZE = 224                      # VGG19
IMG_SHAPE = (IMG_SIZE, IMG_SIZE, 3)
num_classes = 100                   # cifar100

# 사전 훈련된 모델 VGG19 에서 기본 모델을 생성합니다.
base_model = tf.keras.applications.VGG19(input_shape=IMG_SHAPE,
                                               include_top=True,
                                               weights='imagenet')

base_model.summary()

# define new empty model
model = Sequential()

# add all layers except output from VGG19 to new model
for layer in base_model.layers[:-3]:
    model.add(layer)
    
base_model.trainable = False

# freeze all weights
# for layer in model.layers:
#     layer.trainable = False

# add dropout layer and new output layer
model.add(Dropout(0.3))
model.add(Dense(units=2048, activation='relu'))
model.add(Dropout(0.3))
model.add(Dense(units=1024, activation='relu'))
model.add(Dropout(0.3))
model.add(Dense(num_classes, activation='softmax'))
model.summary()


model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['categorical_accuracy'])
model_name = 'cifar100_VGG19'

# Load the CIFAR-100 dataset
cifar100 = tf.keras.datasets.cifar100

# load dataset
(X_train, Y_train) , (X_test, Y_test) = cifar100.load_data()

# Onehot encode labels
Y_train = tf.keras.utils.to_categorical(Y_train, num_classes)
Y_test = tf.keras.utils.to_categorical(Y_test, num_classes)

train_size = 250
test_size = 500
training_epoch = 3
STEPS = int(50000/train_size)

import os.path
if os.path.isfile(model_name+'.h5'):
    model.load_weights(model_name+'.h5')

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

for e in range(training_epoch):
    train_loss = 0
    train_acc = 0

    for s in range(STEPS):
        x_batch, y_batch = getBatch(train_size, "train")
        out = model.train_on_batch(x_batch, y_batch)
        train_loss += out[0]
        train_acc += out[1]

    print(f"Epoch: {e+1}\nTraining Loss = {train_loss / STEPS}\tTraining Acc = {train_acc / STEPS}")

    x_batch_val, y_batch_val = getBatch(test_size, "val")
    eval = model.evaluate(x_batch_val, y_batch_val)
    print(f"Validation loss: {eval[0]}\tValidation Acc: {eval[1]}\n")
    
model.save_weights(model_name+'.h5', overwrite=True)

# Sample outputs from validation set
LABELS_LIST = [
    'apple', 'aquarium_fish', 'baby', 'bear', 'beaver', 'bed', 'bee', 'beetle', 
    'bicycle', 'bottle', 'bowl', 'boy', 'bridge', 'bus', 'butterfly', 'camel', 
    'can', 'castle', 'caterpillar', 'cattle', 'chair', 'chimpanzee', 'clock', 
    'cloud', 'cockroach', 'couch', 'crab', 'crocodile', 'cup', 'dinosaur', 
    'dolphin', 'elephant', 'flatfish', 'forest', 'fox', 'girl', 'hamster', 
    'house', 'kangaroo', 'keyboard', 'lamp', 'lawn_mower', 'leopard', 'lion',
    'lizard', 'lobster', 'man', 'maple_tree', 'motorcycle', 'mountain', 'mouse',
    'mushroom', 'oak_tree', 'orange', 'orchid', 'otter', 'palm_tree', 'pear',
    'pickup_truck', 'pine_tree', 'plain', 'plate', 'poppy', 'porcupine',
    'possum', 'rabbit', 'raccoon', 'ray', 'road', 'rocket', 'rose',
    'sea', 'seal', 'shark', 'shrew', 'skunk', 'skyscraper', 'snail', 'snake',
    'spider', 'squirrel', 'streetcar', 'sunflower', 'sweet_pepper', 'table',
    'tank', 'telephone', 'television', 'tiger', 'tractor', 'train', 'trout',
    'tulip', 'turtle', 'wardrobe', 'whale', 'willow_tree', 'wolf', 'woman',
    'worm'
]

x_batch_val, y_batch_val = getBatch(10, "val")

for i in range(10):
    import numpy as np
    plt.imshow(x_batch_val[i])
    plt.show()
    print("pred: " + LABELS_LIST[np.argmax(model.predict(x_batch_val[i:i+1]))])
    print("acct: " + LABELS_LIST[np.argmax(y_batch_val[i])])

