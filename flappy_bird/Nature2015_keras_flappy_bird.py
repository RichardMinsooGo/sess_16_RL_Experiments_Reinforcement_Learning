#!/usr/bin/env python
from __future__ import print_function

import argparse
import skimage as skimage
from skimage import transform, color, exposure
from skimage.transform import rotate
from skimage.viewer import ImageViewer

import tensorflow as tf
import numpy as np
import random
from collections import deque
import os
import sys
sys.path.append("game/")
import wrapped_flappy_bird as game
import time

import json
from keras.initializers import normal, identity
from keras.models import model_from_json
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation, Flatten
from keras.layers.convolutional import Convolution2D, MaxPooling2D
from keras.optimizers import SGD , Adam

FRAME_PER_ACTION = 1
game_name = 'bird_dqn_Keras'            # the name of the game being played for log files
CONFIG = 'nothreshold'
action_size = 2               # number of valid actions
discount_factor = 0.99        # decay rate of past observations
OBSERVATION = 3200.           # timesteps to observe before training
EXPLORE = 3000000.            # frames over which to anneal epsilon
FINAL_EPSILON = 0.0001        # final value of epsilon
INITIAL_EPSILON = 0.1         # starting value of epsilon
size_replay_memory = 50000    # number of previous transitions to remember
batch_size = 32                    # size of minibatch
LEARNING_RATE = 1e-4

img_rows , img_cols = 80, 80
#Convert image into Black and white
img_channels = 4 #We stack 4 frames

model_path = "save_model/" + game_name
graph_path = "save_graph/" + game_name

# Make folder for save data
if not os.path.exists(model_path):
    os.makedirs(model_path)
if not os.path.exists(graph_path):
    os.makedirs(graph_path)

def build_model():
    print("Now we build the model")
    model = Sequential()
    model.add(Convolution2D(32, 8, 8, subsample=(4, 4), border_mode='same',input_shape=(img_rows,img_cols,img_channels)))  #80*80*4
    model.add(Activation('relu'))
    model.add(Convolution2D(64, 4, 4, subsample=(2, 2), border_mode='same'))
    model.add(Activation('relu'))
    model.add(Convolution2D(64, 3, 3, subsample=(1, 1), border_mode='same'))
    model.add(Activation('relu'))
    model.add(Flatten())
    model.add(Dense(512))
    model.add(Activation('relu'))
    model.add(Dense(2))
   
    adam = Adam(lr=LEARNING_RATE)
    model.compile(loss='mse',optimizer=adam)
    print("We finish building the model")
    return model

def train_model(model):
    
    model.load_weights(model_path+"/model.h5")
    print("\n\n Successfully loaded \n\n")
    # open up a game state to communicate with emulator
    game_state = game.GameState()

    # store the previous observations in replay memory
    memory = deque()

    # get the first state by doing nothing and preprocess the image to 80x80x4
    do_nothing = np.zeros(action_size)
    do_nothing[0] = 1
    state, reward_0, done = game_state.frame_step(do_nothing)

    state = skimage.color.rgb2gray(state)
    state = skimage.transform.resize(state,(80,80))
    state = skimage.exposure.rescale_intensity(state,out_range=(0,255))

    state = state / 255.0

    stacked_state = np.stack((state, state, state, state), axis=2)
    #print (stacked_state.shape)

    #In Keras, need to reshape
    stacked_state = stacked_state.reshape(1, stacked_state.shape[0], stacked_state.shape[1], stacked_state.shape[2])  #1*80*80*4
    
    OBSERVE = OBSERVATION
    epsilon = INITIAL_EPSILON
    
    start_time = time.time()
    time_step = 0
    # while (True):
    while time.time() - start_time < 5*60:
        loss = 0
        Q_sa = 0
        action_index = 0
        reward = 0
        episode_step = 0
        while not terminal and episode_step < 1000:
            episode_step += 1
            action = np.zeros([action_size])
            #choose an action epsilon greedy
            if time_step % FRAME_PER_ACTION == 0:
                if random.random() <= epsilon:
                    # print("----------Random Action----------")
                    action_index = random.randrange(action_size)
                    action[action_index] = 1
                else:
                    Q_value = model.predict(stacked_state)       #input a stack of 4 images, get the prediction
                    max_Q = np.argmax(Q_value)
                    action_index = max_Q
                    action[max_Q] = 1

            #We reduced the epsilon gradually
            if epsilon > FINAL_EPSILON and time_step > OBSERVE:
                epsilon -= (INITIAL_EPSILON - FINAL_EPSILON) / EXPLORE

            #run the selected action and observed next state and reward
            next_state_colored, reward, done = game_state.frame_step(action)

            next_state = skimage.color.rgb2gray(next_state_colored)
            next_state = skimage.transform.resize(next_state,(80,80))
            next_state = skimage.exposure.rescale_intensity(next_state, out_range=(0, 255))

            next_state = next_state / 255.0

            next_state = next_state.reshape(1, next_state.shape[0], next_state.shape[1], 1) #1x80x80x1
            stacked_next_state = np.append(next_state, stacked_state[:, :, :, :3], axis=3)

            # store the transition in memory
            memory.append((stacked_state, action_index, reward, stacked_next_state, done))
            if len(memory) > size_replay_memory:
                memory.popleft()

            # only train if done observing
            if time_step > OBSERVE:
                # sample a minibatch to train on
                minibatch = random.sample(memory, batch_size)

                #Now we do the experience replay
                states, actions, rewards, next_states, done = zip(*minibatch)
                states      = np.concatenate(states)
                next_states = np.concatenate(next_states)
                targets     = model.predict(states)
                Q_sa        = model.predict(next_states)
                targets[range(batch_size), actions] = rewards + discount_factor*np.max(Q_sa, axis=1)*np.invert(done)

                loss += model.train_on_batch(states, targets)

            # update the old values
            stacked_state = stacked_next_state
            time_step += 1
            
            # print info
            progress = ""
            if time_step <= OBSERVE:
                progress = "observe"
            elif time_step > OBSERVE and time_step <= OBSERVE + EXPLORE:
                progress = "explore"
            else:
                progress = "train"

            if episode_step % 500 == 0:
                print("TIMESTEP :", time_step, \
                      "/ STATE :", progress, "/ EPSILON :", epsilon)
                if epsode_step % 1000 == 0:
                    break
            
    print("\n\n Now we save model \n\n")
    model.save_weights(model_path+"/model.h5")
    with open(model_path+"/model.json", "w") as outfile:
        json.dump(model.to_json(), outfile)
                    
    print("Episode finished!")
    print("************************")
    
def main():
    model = build_model()
    train_model(model)

if __name__ == "__main__":
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    sess = tf.Session(config=config)
    from keras import backend as K
    K.set_session(sess)
    main()
