import torch
from collections import OrderedDict
from src.models.ClassYEncoders import *
from src.models.LabelDecoders import *
from src.lightning_modules.One_Stage import *
from src.lightning_modules.Two_Stage import *
import os
from src.models.WRN import *
from src.models.CNN import *
from torch.utils.data import DataLoader
import json
import torchvision.transforms as transforms
import torch.utils.data as data
from torchvision.datasets import MNIST, FashionMNIST, CIFAR10, SVHN, CIFAR100
from src.models.TemperatureScaler import *

EVAL_PATH = "./experiment_results/robustness_evaluations/"

def load_WRN_model(path, dataset="CIFAR10", map_location="cpu", clean_dict_keys=True):
    if dataset.find("CIFAR100") != -1:
        model = WideResNet(num_classes=100, depth=28, width=10, num_input_channels=3)
    elif dataset.find("CIFAR10") != -1 or dataset.find("SVHN") != -1:
        model = WideResNet(num_classes=10, depth=28, width=10, num_input_channels=3)
    checkpoint = torch.load(path, map_location=map_location)
    checkpoint_cleaned = OrderedDict()
    for key in checkpoint['state_dict'].keys():
        new_key = ".".join(key.split(".")[1:])
        checkpoint_cleaned[new_key] = checkpoint['state_dict'][key]
    model.load_state_dict(checkpoint_cleaned)
    return model

# TODO: write new function load_model that has input argument model if this works
def load_CNN_model(path, dataset="CIFAR10", map_location="cpu", clean_dict_keys=True):
    if dataset.find("CIFAR100") != -1:
        model = CNN(num_classes=100)
    elif dataset.find("CIFAR10") != -1 or dataset.find("SVHN") != -1:
        model = CNN(num_classes=10)
    checkpoint = torch.load(path, map_location=map_location)
    checkpoint_cleaned = OrderedDict()
    for key in checkpoint['state_dict'].keys():
        new_key = ".".join(key.split(".")[1:])
        checkpoint_cleaned[new_key] = checkpoint['state_dict'][key]
    model.load_state_dict(checkpoint_cleaned)
    return model

def construct_ClassYEncoder(dataset, latent_dim, num_layers=3, simple_CNN=False):
    if simple_CNN:
        return CNNHead(latent_dim)
    elif num_layers == 4:
        return WRN2810HeadMLP4(latent_dim)
    elif num_layers == 5:
        return WRN2810HeadMLP5(latent_dim)
    return WRN2810Head(latent_dim)

def construct_EncoderVar(dataset, latent_dim, num_layers=3, simple_CNN=False):
    if simple_CNN:
        return CNNVarHead(latent_dim)
    elif num_layers == 4:
        return WRN2810VarHeadMLP4(latent_dim)
    elif num_layers == 5:
        return WRN2810VarHeadMLP5(latent_dim)
    return WRN2810VarHead(latent_dim)

def construct_LabelDecoder(dataset, latent_dim, num_classes, simple_CNN=False):
    return CIFAR10SimpelLabelDecoder(latent_dim, num_classes=num_classes)

def reset_CIFA10LabelDecoder(num_classes):
    return CIFAR10SimpelLabelDecoder(64*WIDERESNET_WIDTH_WANG2023, num_classes=num_classes)

def construct_ClassYEncoderBody(pretrained_model=None, simple_CNN=False):
    if pretrained_model is None:
        if simple_CNN:
            return CNNBody()
        else:
            return WRN2810Body(num_classes=10, depth=28, width=10, num_input_channels=3)
    else:
        pretrained_dict =  pretrained_model.state_dict()
        if simple_CNN:
            encoder_model = CNNBody()
        else:
            encoder_model = WRN2810Body(num_classes=10, depth=28, width=10, num_input_channels=3)
        encoder_dict = encoder_model.state_dict()
        pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in encoder_dict}
        encoder_dict.update(pretrained_dict)
        encoder_model.load_state_dict(encoder_dict)
        return encoder_model
        

def load_model(name, path, device="cuda:0"):
    if name.find("VTST") != -1:
        return VTST_Module.load_from_checkpoint(path, map_location=device).model
    elif name.find("TST") != -1:
        return TS_Module.load_from_checkpoint(path, map_location=device).model
    elif name == "WRN" or name == "CNN":
         return lt_disc_models.load_from_checkpoint(path, map_location=device).model
    elif name == "REINIT":
        return TS_Module.load_from_checkpoint(path, map_location=device).model


def get_valid_loader(dataset, batch_size):
    if dataset == "MNIST":
        train_dataset = MNIST(os.getcwd()+"/data/", download=True, transform=transforms.ToTensor(), train=True)
        num_classes = 10
    elif dataset == "FMNIST":
        train_dataset = FashionMNIST(os.getcwd()+"/data/", download=True, transform=transforms.ToTensor(), train=True)
        num_classes = 10 
    elif dataset == "CIFAR10":
        transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.4914, 0.4822, 0.4465),  (0.247, 0.243, 0.261))])
        train_dataset = CIFAR10(os.getcwd()+"/data/", download=True, transform=transform, train=True)
        num_classes = 10 
    elif dataset == "CIFAR100":
        transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.5074,0.4867,0.4411),(0.2011,0.1987,0.2025))])
        train_dataset = CIFAR100(os.getcwd()+"/data/", download=True, transform=transform, train=True)
        num_classes = 100
    elif dataset == "SVHN":
        transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.4914, 0.4822, 0.4465),  (0.2023, 0.1994, 0.2010))])
        train_dataset = SVHN(os.getcwd()+"/data/", download=True, transform=transform, split="train")
        num_classes = 10 
    if dataset == "CIFAR100":
        valid_proportion = 0.95
    else:
        valid_proportion = 0.8
    train_set_size = int(len(train_dataset) * valid_proportion)
    valid_set_size = len(train_dataset) - train_set_size
    torch_seed = torch.Generator()
    torch_seed.manual_seed(1)
    train_set, valid_set = data.random_split(train_dataset, [train_set_size, valid_set_size], generator=torch_seed)
    train_loader = DataLoader(train_set, batch_size=batch_size)
    valid_loader = DataLoader(valid_set, batch_size=batch_size)
    return valid_loader

def temperature_scale_model(model, dataset, batch_size):
    temperature_wrapper = ModelWithTemperature(model)
    valid_loader = get_valid_loader(dataset, batch_size)
    temperature_wrapper.set_temperature(valid_loader)
    return temperature_wrapper