import cv2
import torch
import pickle
from torchvision import transforms
from PIL import Image
from parameters import *
from faceDetector import *
import torch.nn.functional as F

def load_database():
    with open("./database.p", "rb") as f:
        database = pickle.load(f)
    return database

def load_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = torch.hub.load('pytorch/vision:v0.10.0', 'mobilenet_v2', pretrained = True)
    model = model.to(device)
    model.load_state_dict(torch.load("facenet_model.pth"))
    model.eval()
    return model

def preprocees(image):
    transform = transforms.Compose([
        transforms.Resize(IMAGE_SIZE),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ])
    return transform(image)

def img_to_encoding(image_tensor, model, device):
    image_tensor = preprocees(image_tensor).unsqueeze(0).to(device)
    with torch.no_grad():
        return model(image_tensor)

def similarity_score(firstEmbedding, secondEmbedding):
    return F.cosine_similarity(firstEmbedding, secondEmbedding)

def faceDetector(faceDetector, image_path):    
    image = cv2.imread(image_path)
    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faceRects = faceDetector.detect(gray_img)
    for (x, y, w, h) in faceRects:
        left, top, right, bottom = x, y, x + w, y + h
        face = image[top : bottom, left : right]
    return torch.from_numpy(face), faceRects

def Recognized(testEmbedding, database):
    min_dist = 1000
    face_name = ""
    for face in database.keys():
        similarityScore = similarity_score(database[face], testEmbedding)
        if similarityScore < min_dist:
            min_dist = similarityScore
            face_name = face
    return face_name

def faceRecognition(image_path):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model()
    image = Image.open(image_path).convert("RGB")
    database = load_database()
    fd = faceDetector('haarcascade_frontalface_default.xml')
    image_tensor, faceRects = faceDetector(fd, image_path)
    testEmbedding = img_to_encoding(image_tensor, model, device)
    face_name = Recognized(testEmbedding, database)

    for (x, y, w, h) in faceRects:
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        font_scale = 0.75
        font_thickness = 2
        text_size = cv2.getTextSize(face_name, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)
        text_x = x + (w - text_size[0]) // 2
        text_y = y - 10
        cv2.putText(image, face_name, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), font_thickness)

    cv2.imshow(image)

