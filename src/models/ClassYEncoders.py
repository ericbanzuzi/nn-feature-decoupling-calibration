# Some code from https://github.com/deepmind/deepmind-research/blob/master/adversarial_robustness/pytorch/model_zoo.py
import torch.nn as nn
import torch
import torch.nn.functional as F
import math
from typing import Tuple, Union
from src.models.ResBlock import *
from src.models.WRN import _BlockGroup
from src.models.ViT import *
from transformers import ViTForImageClassification, ViTImageProcessor, ViTModel, ViTConfig
from data.tinyimagenet import *

WIDERESNET_WIDTH_WANG2023=10
WIDERESNET_WIDTH_MNIST=4
CIFAR10_MEAN = (0.4914, 0.4822, 0.4465)
CIFAR10_STD = (0.2471, 0.2435, 0.2616)


class WRN2810VarHead(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        #The input to the head is the output of the body which is 64*width (where width is the width of the ResNet).
        self.fc1 = nn.Linear(64*WIDERESNET_WIDTH_WANG2023, latent_dim*3)
        self.fc2 = nn.Linear(latent_dim*3, latent_dim)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.logsigmoid(self.fc2(x))
        return x


class WRN2810VarHeadMLP4(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        # The input to the head is the output of the body which is 64*width (where width is the width of the ResNet).
        self.fc1 = nn.Linear(64*WIDERESNET_WIDTH_WANG2023, latent_dim*6)
        self.fc2 = nn.Linear(latent_dim*6, latent_dim*3)
        self.fc3 = nn.Linear(latent_dim*3, latent_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.logsigmoid(self.fc3(x))
        return x


class WRN2810VarHeadMLP5(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        # The input to the head is the output of the body which is 64*width (where width is the width of the ResNet).
        self.fc1 = nn.Linear(64*WIDERESNET_WIDTH_WANG2023, latent_dim*9)
        self.fc2 = nn.Linear(latent_dim*9, latent_dim*6)
        self.fc3 = nn.Linear(latent_dim*6, latent_dim*3)
        self.fc4 = nn.Linear(latent_dim*3, latent_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = F.logsigmoid(self.fc4(x))
        return x


class WRN2810Head(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        #The input to the head is the output of the body which is 64*width (where width is the width of the ResNet).
        self.fc1 = nn.Linear(64*WIDERESNET_WIDTH_WANG2023, latent_dim*3)
        self.fc2 = nn.Linear(latent_dim*3, latent_dim)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class WRN2810HeadMLP4(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        # The input to the head is the output of the body which is 64*width (where width is the width of the ResNet).
        self.fc1 = nn.Linear(64*WIDERESNET_WIDTH_WANG2023, latent_dim*6)
        self.fc2 = nn.Linear(latent_dim*6, latent_dim*3)
        self.fc3 = nn.Linear(latent_dim*3, latent_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


class WRN2810HeadMLP5(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        # The input to the head is the output of the body which is 64*width (where width is the width of the ResNet).
        self.fc1 = nn.Linear(64*WIDERESNET_WIDTH_WANG2023, latent_dim*9)
        self.fc2 = nn.Linear(latent_dim*9, latent_dim*6)
        self.fc3 = nn.Linear(latent_dim*6, latent_dim*3)
        self.fc4 = nn.Linear(latent_dim*3, latent_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        return x



class WRN2810Body(nn.Module):
    """
    Adapted WideResNet model
    Arguments:
        num_classes (int): number of output classes.
        depth (int): number of layers.
        width (int): width factor.
        activation_fn (nn.Module): activation function.
        mean (tuple): mean of dataset.
        std (tuple): standard deviation of dataset.
        padding (int): padding.
        num_input_channels (int): number of channels in the input.
    """
    def __init__(self,
                 num_classes: int = 10,
                 depth: int = 28,
                 width: int = 10,
                 activation_fn: nn.Module = nn.ReLU,
                 mean: Union[Tuple[float, ...], float] = CIFAR10_MEAN,
                 std: Union[Tuple[float, ...], float] = CIFAR10_STD,
                 padding: int = 0,
                 num_input_channels: int = 3):
        super().__init__()
        self.padding = padding
        num_channels = [16, 16 * width, 32 * width, 64 * width]
        assert (depth - 4) % 6 == 0
        num_blocks = (depth - 4) // 6
        self.num_input_channels = num_input_channels
        self.init_conv = nn.Conv2d(num_input_channels, num_channels[0],
                                   kernel_size=3, stride=1, padding=1, bias=False)
        self.layer = nn.Sequential(
            _BlockGroup(num_blocks, num_channels[0], num_channels[1], 1,
                        activation_fn=activation_fn),
            _BlockGroup(num_blocks, num_channels[1], num_channels[2], 2,
                        activation_fn=activation_fn),
            _BlockGroup(num_blocks, num_channels[2], num_channels[3], 2,
                        activation_fn=activation_fn))
        self.batchnorm = nn.BatchNorm2d(num_channels[3], momentum=0.01)
        self.relu = activation_fn(inplace=True)
        #self.fc = nn.Linear(num_channels[3], latent_dim)
        self.num_channels = num_channels[3]
        
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                m.bias.data.zero_()
    
    def forward(self, x):
        if self.padding > 0:
            x = F.pad(x, (self.padding,) * 4)
        out = self.init_conv(x)
        out = self.layer(out)
        out = self.relu(self.batchnorm(out))
        out = F.avg_pool2d(out, 8)
        out = out.view(-1, self.num_channels)
        return out
    
class CNNVarHead(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        #The input to the head is the output of the body which is 64*width (where width is the width of the ResNet).
        self.fc1 = nn.Linear(84, latent_dim*3)
        self.fc2 = nn.Linear(latent_dim*3, latent_dim)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.logsigmoid(self.fc2(x))
        return x

class CNNHead(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        #The input to the head is the output of the body which is 64*width (where width is the width of the ResNet).
        self.fc1 = nn.Linear(84, latent_dim*3)
        self.fc2 = nn.Linear(latent_dim*3, latent_dim)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class CNNBody(nn.Module):
    """
    CNN model
    Arguments:
        num_classes (int): number of output classes.
    """
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 6, 5)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(6, 16, 5)
        self.fc1 = nn.Linear(400, 120)
        self.fc2 = nn.Linear(120, 84)
        #self.fc3 = nn.Linear(84, num_classes) # skip last layer

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = torch.flatten(x, 1) # flatten all dimensions except batch
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        #x = self.fc3(x) # don't use last layer, instead MLP head is added here
        return x


class ViTVarHead(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        #The input to the head is the output of the body which is 64*width (where width is the width of the ResNet).
        self.fc1 = nn.Linear(768, latent_dim*3)
        self.fc2 = nn.Linear(latent_dim*3, latent_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.logsigmoid(self.fc2(x))
        return x

class ViTHead(nn.Module):
    def __init__(self, latent_dim: int = 128):
        super().__init__()
        #The input to the head is the output of the body which is 64*width (where width is the width of the ResNet).
        self.fc1 = nn.Linear(768, latent_dim*3)
        self.fc2 = nn.Linear(latent_dim*3, latent_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class ViTBody(nn.Module):
    """
    ViT model
    Arguments:
        dataset (str): name of the dataset to be used.
        model_name_or_path (str): pretrained weights to be used
    """
    def __init__(self, dataset, model_name_or_path):
        super().__init__()
        if dataset == "CIFAR10":
            labels = [
                "airplane", "automobile", "bird", "cat", "deer",
                "dog", "frog", "horse", "ship", "truck"
            ]
        elif dataset == "TINYIMAGENET":
            labels = get_tinyimagenet_labels_from_dataset(os.getcwd()+"/data/")
        else:
             raise Exception("Oops, this dataset cannot be combined with a ViT!")

        config = ViTConfig.from_pretrained(model_name_or_path)
        config.add_pooling_layer = False
        config.num_labels = len(labels)
        config.id2label = {str(i): c for i, c in enumerate(labels)}
        config.label2id = {c: str(i) for i, c in enumerate(labels)}
        self.vit = ViTModel.from_pretrained(
                        model_name_or_path,
                        config=config
                    )
        #print("When initializing the ViTBody, these are the keys of the weights dict:")
        #print(self.vit.state_dict().keys())

    def forward(self, x):
        outputs = self.vit(x)
        sequence_output = outputs[0]

        return sequence_output[:, 0, :]
