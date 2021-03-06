from drugai import *
# import os.path
np.random.seed(2019)


def Gan(lr=0.001):
    opt = keras.optimizers.Adam(lr, beta_1=0.5, beta_2=0.9)
    D.compile(loss=[wasserstein_loss,'categorical_crossentropy'], optimizer=opt)
    GAN=keras.models.Model(inputs=G.input, outputs=D(G.output))
    opt = keras.optimizers.Adam(lr, beta_1=0.5, beta_2=0.9)
    GAN.compile(loss=[wasserstein_loss,'categorical_crossentropy'], optimizer=opt)
    D.trainable= True
    
    D.trainable=False
    D.compile(loss=[wasserstein_loss,'categorical_crossentropy'], optimizer=opt)
    G.compile(optimizer=opt, loss='mse', metrics=['accuracy'])
   
    print ("input_shape"+ str(GAN.input_shape)+"\noutput_shape"+ str(GAN.output_shape))
    return GAN,D,G



BATCH_SIZE = 32
HALF_BATCH = BATCH_SIZE / 2
CLIP = 0.01
epochs = 1
n_critic = 5
latent_size=2

# read csv file
###############################################################################
###
### Sequence Data
###
###############################################################################

# read csv file
data = pd.read_csv('stahl.csv')
data = data.reindex(np.random.permutation(data.index))
# data=data.head(30)
Y = data.SMILES
Y.head()
X = data.ix[:, 1:7]
X = X.values
X = X.astype('int')
type(X)

Y=Y[0:100]

# padding smiles to same length by adding "|" at the end of smiles
maxY = Y.str.len().max() + 11
y = Y.str.ljust(maxY, fillchar='|')
ts = y.str.len().max()
print ("ts={0}".format(ts))
# CharToIndex and IndexToChar functions
chars = sorted(list(set("".join(y.values.flatten()))))
print('total chars:', len(chars))

char_idx = dict((c, i) for i, c in enumerate(chars))
idx_char = dict((i, c) for i, c in enumerate(chars))

y_dash = dimY(y, ts, char_idx, chars)

print("Shape\n Y={0}".format( y_dash.shape))


###############################################################################
###
### Image Data
###
###############################################################################
(_, _), (X_test, _) = tf.keras.datasets.mnist.load_data()
X_test=X_test.astype('float32') / 255.
X_test=X_test[0:100]
del _

##############ReSizing Images if needed)#########
y_dash_img=mnist_resize(X_test,y_dash.shape[1],y_dash.shape[2])
plot_mnist(y_dash_img[0:4])

#additional channel adding for 2D convolution
y_dash_img=dim_chg(y_dash_img)
y_dash=dim_chg(y_dash)

"""  
#Padding with zeros
r=y_dash.shape[1]-X_test.shape[1]
c=y_dash.shape[2]-X_test.shape[2]
y_dash_img=np.pad(X_test, pad_width=((0, 0), (0, r),(0,c)), mode='constant')
print("Image shape: "+str(y_dash_img.shape))
"""

G = Generator2D()
D = Discriminator2D()
GAN, D,G = Gan()
# enable training in discrimator


valid=-np.ones((BATCH_SIZE, 1))
fake=np.ones((BATCH_SIZE, 1))
'''
valid = np.ones((BATCH_SIZE, 1))
fake = np.zeros((BATCH_SIZE, 1))
'''
for epoch in range(epochs):
    for _ in range(n_critic):
        
        
        # -----------------------------
        #  Train Discriminator Images
        # -----------------------------
         # Select a random half batch of images
        idx = np.random.randint(0, y_dash_img.shape[0], BATCH_SIZE)
        imgs = y_dash_img[idx]

        # noise = np.random.normal(0, 1, (BATCH_SIZE, 100))
        noise =  np.random.normal(0, 1, (BATCH_SIZE, latent_size))
        #task
        tasks = np.zeros((BATCH_SIZE,2))
        tasks[:,0]=1
       # tasks= np.zeros((BATCH_SIZE,1))
        # Generate a half batch of new images
        gen_imgs= G.predict([noise,tasks])

         # Train the discriminator
        d_loss_real = D.train_on_batch(imgs, [valid,tasks])  # linear activation
        d_loss_fake = D.train_on_batch(gen_imgs, [fake,tasks])
        d_loss = 0.5 * np.add(d_loss_fake, d_loss_real)
        
        # ------------------------------
        #  Train Discriminator Sequence
        # ------------------------------
        
        # Select a random half batch of sequence
        idx = np.random.randint(0, y_dash.shape[0], BATCH_SIZE)
        imgs = y_dash[idx]

        # noise = np.random.normal(0, 1, (BATCH_SIZE, 100))
        #noise =  np.random.normal(0, 1, (BATCH_SIZE, latent_size))
        #task
        tasks = np.zeros((BATCH_SIZE,2))
        tasks[:,1]=1  
        #tasks= np.ones((BATCH_SIZE,1))
        # Generate a half batch of new sequence
        gen_imgs = G.predict([noise,tasks])
        
        # Train the discriminator
        d_loss_real = D.train_on_batch(imgs, [valid,tasks])  # linear activation
        d_loss_fake = D.train_on_batch(gen_imgs, [fake,tasks])
        d_loss = (d_loss+0.5 * np.add(d_loss_fake, d_loss_real))/2
        
         # Clip discriminator weights
        for l in D.layers:
            weights = l.get_weights()
            weights = [np.clip(w, -CLIP, CLIP) for w in weights]
            l.set_weights(weights)
        
        # ---------------------------
        #  Train Generator  Images
        # ---------------------------

        noise = np.random.normal(0, 1, (BATCH_SIZE, 2))
        tasks = np.zeros((BATCH_SIZE,2))
        tasks[:,0]=1
        #tasks= np.zeros((BATCH_SIZE,1))
        # Train the generator
        g_loss1 = GAN.train_on_batch([noise,tasks], [valid,tasks])  # linear activation
        
        # ---------------------------
        #  Train Generator  Sequence
        # ---------------------------
        tasks = np.zeros((BATCH_SIZE,2))
        tasks[:,1]=1  
        #tasks= np.ones((BATCH_SIZE,1))
        # Train the generator
        g_loss2 = GAN.train_on_batch([noise,tasks], [valid,tasks])  # linear activation
        g_loss=np.add(g_loss1,g_loss2)*0.5
    print("Epoch: "+str(epoch)+"|"+str(epochs))
    print("G Loss: "+str(g_loss))
    print("D Loss: "+str(d_loss))
    if epoch % ( 25) == 0:
        G.save("Gen.h5")

        # For Prediction
        # start Prediction

        #Ghash = Generator(y_dash)
        print("Prediction")
        #Ghash.load_weights('Gen1.h5')
        print("Predicted Images")
        noise =  np.random.normal(0, 1, (4, latent_size))
        tasks = np.zeros((4,2))
        tasks[:,0]=1 
        #tasks =  np.zeros((4,1))
        preds = G.predict([noise,tasks])
        preds=dim_chg(preds,drop=True)
        preds= preds[:,0:116,0:y_dash.shape[2]]
        plot_mnist(preds)
        print("Predicted Sequence")
        tasks = np.zeros((4,2))
        tasks[:,1]=1 
        #tasks =  np.ones((4,1))
        preds = G.predict([noise,tasks])
        preds=dim_chg(preds,drop=True)
        y_pred = prediction(preds)
        y_pred = seq_txt(y_pred, idx_char)
        s = smiles_output(y_pred)
        print(s)
