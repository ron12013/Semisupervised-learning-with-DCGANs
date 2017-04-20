import numpy as np
from sklearn.utils import shuffle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from PIL import Image
import argparse
import math

from keras.models import Sequential, Model
from keras.callbacks import ModelCheckpoint
from keras.layers import Dense, Input
from keras.layers import Reshape
from keras.layers.core import Activation
from keras.layers.normalization import BatchNormalization
from keras.layers.convolutional import UpSampling2D, UpSampling3D
from keras.layers.convolutional import Convolution2D, MaxPooling2D, Deconvolution2D
from keras.layers.advanced_activations import LeakyReLU
from keras.callbacks import EarlyStopping
from keras.layers.core import Flatten
from keras.optimizers import SGD, Adam
from keras.datasets import mnist, cifar10
from keras.utils import np_utils


def Generator():
    model = Sequential()
    model.add(Dense(input_dim=100, output_dim=2048, init='normal'))
    model.add(BatchNormalization())
    model.add(Activation('tanh'))
    model.add(Reshape((2, 2, 512), input_dim=2048)) 
    model.add(UpSampling2D(size=(2, 2)))
    model.add(Convolution2D(256, 5, 5, border_mode='same'))
    model.add(BatchNormalization())
    model.add(Activation('tanh'))
    model.add(UpSampling2D(size=(2, 2)))
    model.add(Convolution2D(128, 5, 5, border_mode='same'))
    model.add(BatchNormalization())
    model.add(Activation('tanh'))
    model.add(UpSampling2D(size=(2, 2)))
    model.add(Convolution2D(64, 5, 5, border_mode='same'))
    model.add(BatchNormalization())
    model.add(Activation('tanh'))
    model.add(UpSampling2D(size=(2, 2)))
    model.add(Convolution2D(3, 5, 5, border_mode='same'))
    model.add(Activation('tanh'))
    print model.summary()
    return model


def Discriminator():
    model = Sequential()
    model.add(Convolution2D(64, 5, 5, border_mode='same',subsample=(2, 2), input_shape=(32, 32, 3)))
    model.add(LeakyReLU(0.2))
    model.add(Convolution2D(128, 5, 5, border_mode='same', subsample=(2,2)))
    model.add(LeakyReLU(0.2))
    model.add(Convolution2D(256, 5, 5, border_mode='same', subsample=(2,2)))
    model.add(LeakyReLU(0.2))
    model.add(Convolution2D(512, 5, 5, border_mode='same', subsample=(4,4)))
    model.add(LeakyReLU(0.2))
    model.add(Flatten())
    model.add(Dense(1))
    model.add(Activation('sigmoid'))

    print model.summary()
    return model

def generator_containing_discriminator(generator, discriminator):
    model = Sequential()
    model.add(generator)
    discriminator.trainable = False
    model.add(discriminator)
    return model

def combine_images(generated_images):
    num = generated_images.shape[0]
    width = int(math.sqrt(num))
    height = int(math.ceil(float(num)/width))
    generated_images = generated_images.reshape((generated_images.shape[0], 32, 32, 3) )
    shape = generated_images.shape[1:3]
    image = np.zeros((height*shape[0], width*shape[1], 3),
                     dtype=generated_images.dtype)
    for index, img in enumerate(generated_images):
        i = int(index/width)
        j = index % width
        image[i*shape[0]:(i+1)*shape[0], j*shape[1]:(j+1)*shape[1], 0] = \
            img[:, :, 0]
	image[i*shape[0]:(i+1)*shape[0], j*shape[1]:(j+1)*shape[1], 1] = \
            img[:, :, 1]
	image[i*shape[0]:(i+1)*shape[0], j*shape[1]:(j+1)*shape[1], 2] = \
            img[:, :, 2]
    return image

def train(BATCH_SIZE, epoch_num):
    (X_train, y_train), (X_test, y_test) = cifar10.load_data()
    X_train = X_train.astype('float32')
    X_test = X_test.astype('float32')
    X_train = (X_train - 127.5)/127.5
    X_test /= 255
    X_train = X_train.reshape((X_train.shape[0], ) + X_train.shape[1:])

    discriminator = Discriminator()
    generator = Generator()
    discriminator_on_generator = \
        generator_containing_discriminator(generator, discriminator)
    d_optim = Adam(lr=0.0002, beta_1=0.5, beta_2=0.999, epsilon=1e-08, decay=0.0)
    g_optim = Adam(lr=0.0002, beta_1=0.5, beta_2=0.999, epsilon=1e-08, decay=0.0)
    generator.compile(loss='binary_crossentropy', optimizer="Adam")
    discriminator_on_generator.compile(
        loss='binary_crossentropy', optimizer=g_optim)
    discriminator.trainable = True
    discriminator.compile(loss='binary_crossentropy', optimizer=d_optim)
    noise = np.zeros((BATCH_SIZE, 100))
    for epoch in range(100):
        batches_num = int(X_train.shape[0]/BATCH_SIZE)
        print("Epoch is", epoch)
        print("Number of batches", int(X_train.shape[0]/BATCH_SIZE))
        for index in range(batches_num):
            for i in range(BATCH_SIZE):
                noise[i, :] = np.random.uniform(-1, 1, 100)
                #print 'noise', noise.dtype
            discriminator.trainable = False
            g_loss = discriminator_on_generator.train_on_batch(
                noise, [0.9] * BATCH_SIZE)
            filepath="weights-improvement-{epoch:02d}-{val_acc:.2f}.hdf5"
            checkpoint = ModelCheckpoint(filepath, monitor='val_acc', verbose=1, save_best_only=True, mode='max')
            callbacks_list = [checkpoint]
            discriminator.trainable = True
            print("epoch %d/%d batch %d/%d g_loss : %f" % (epoch+1, epoch_num,index, batches_num, g_loss))

            for i in range(BATCH_SIZE):
                noise[i, :] = np.random.uniform(-1, 1, 100)
            image_batch = X_train[index*BATCH_SIZE:(index+1)*BATCH_SIZE]
            generated_images = generator.predict(noise, verbose=0)
            if index % 80 == 0:
                image = combine_images(generated_images)
                image = image*127.5+127.5
                Image.fromarray(image.astype(np.uint8)).save('images/'+
                    str(epoch)+"_"+str(index)+".png")
            #print image_batch.shape, generated_images.shape
            X = np.concatenate((image_batch, generated_images))

            y = [0.9] * BATCH_SIZE + [0.0] * BATCH_SIZE
            #y = np.array(y)
            #print 'y ', y.shape
            d_loss = discriminator.train_on_batch(X, y)
            print("epoch %d/%d batch %d/%d d_loss : %f" % (epoch+1, epoch_num, index, batches_num, d_loss))


            if index % 20 == 0:
                generator.save_weights('generator_cifar', True)
                discriminator.save_weights('discriminator_cifar', True)



def generate(BATCH_SIZE):
    generator = Generator()
    d_optim = Adam(lr=0.0002, beta_1=0.5, beta_2=0.999, epsilon=1e-08, decay=0.0)
    g_optim = Adam(lr=0.0002, beta_1=0.5, beta_2=0.999, epsilon=1e-08, decay=0.0)
    generator.compile(loss='binary_crossentropy', optimizer=g_optim)
    generator.load_weights('generator_cifar')
    noise = np.zeros((BATCH_SIZE, 100))
    for i in range(BATCH_SIZE):
    	noise[i, :] = np.random.uniform(-1, 1, 100)
    generated_images = generator.predict(noise, verbose=1)
    image = combine_images(generated_images)
    image = image*127.5+127.5
    Image.fromarray(image.astype(np.uint8)).save(
        "generated_image.png")

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str)
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--nice", dest="nice", action="store_true") 
    parser.add_argument("--epoch_num",type=int,default=100)
    parser.set_defaults(nice=False)
    args = parser.parse_args()
    return args


if __name__ == "__main__":

    if not os.path.exists('images'):
        os.mkdir('images')
    args = get_args()
    if args.mode == "train":
        print ('total epochs of the train:'+str(args.epoch_num))
        train(BATCH_SIZE=args.batch_size, epoch_num=args.epoch_num)
    elif args.mode == "generate":
        generate(BATCH_SIZE=args.batch_size)
