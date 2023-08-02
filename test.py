import torch
import pickle
import torch.nn as nn
from torchvision import transforms
from PIL import Image
from data import *
from parameters import *
from facenet_pytorch import InceptionResnetV1
import cv2
import sys
import numpy as np
from loss import *
import imutils
from faceDetector import *

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = InceptionResnetV1(pretrained='vggface2')
model = model.to(device)
model.load_state_dict(torch.load("facenet_model.pth"))
model.eval()

transform = transforms.Compose([
    transforms.Resize((160, 160)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
])

with open("./path_dict.p", "rb") as f:
    paths = pickle.load(f)

faces = []
for key in paths.keys():
    paths[key] = paths[key].replace("\\", "/")
    faces.append(key)

images = {}
for key in paths.keys():
    li = []
    for img in os.listdir(paths[key]):
        img1 = cv2.imread(os.path.join(paths[key],img))
        img2 = img1[...,::-1]
        li.append(np.around(np.transpose(img2, (2,0,1))/255.0, decimals=12))
    images[key] = np.array(li)

if(len(faces) == 0):
    print("No images found in database!!")
    print("Please add images to database")
    sys.exit()

def img_to_encoding(image_path, model, path=True):
    if path == False:
      img1 = image_path
    else:
      img1 = cv2.imread(image_path, 1)
    img = img1[...,::-1]
    img = np.around(np.transpose(img, (2,0,1))/255.0, decimals=12)
    x_train = np.array([img])
    print(x_train.shape)
    embedding = model.predict_on_batch(x_train)
    return embedding

def verify(image_path, identity, database, model):
    
    encoding = img_to_encoding(image_path, model, False)
    min_dist = 1000
    for  pic in database:
        dist = np.linalg.norm(encoding - pic)
        if dist < min_dist:
            min_dist = dist
    print(identity + ' : ' +str(min_dist)+ ' ' + str(len(database)))
    
    if min_dist<THRESHOLD:
        door_open = True
    else:
        door_open = False
        
    return min_dist, door_open

database = {}
for face in faces:
    database[face] = []

for face in faces:
    for img in os.listdir(paths[face]):
        database[face].append(img_to_encoding(os.path.join(paths[face],img), model))

camera = cv2.VideoCapture(0)
fd = faceDetector('haarcascade_frontalface_default.xml')

fourcc = cv2.VideoWriter_fourcc(*'XVID') #codec for video
out = cv2.VideoWriter('output.avi', fourcc, 20, (800, 600) )#Output object

while True:
    ret, frame = camera.read()
    frame = imutils.resize(frame, width = 800)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    print(frame.shape)
    faceRects = fd.detect(gray)
    for (x, y, w, h) in faceRects:
        roi = frame[y:y+h,x:x+w]
        roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        roi = cv2.resize(roi,(IMAGE_SIZE, IMAGE_SIZE))
        min_dist = 1000
        identity = ""
        detected  = False
        
        for face in range(len(faces)):
            person = faces[face]
            dist, detected = verify(roi, person, database[person], model)
            if detected == True and dist<min_dist:
                min_dist = dist
                identity = person
        if detected == True:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, identity, (x+ (w//2),y-2), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), lineType=cv2.LINE_AA)
            
    cv2.imshow('frame', frame)
    out.write(frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
out.release()
cv2.destroyAllWindows()