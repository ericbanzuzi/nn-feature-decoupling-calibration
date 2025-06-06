import torch
import torch.nn as nn
import torch.nn.functional as F
from src.utils.utils import *
from torch import flatten
import torch.optim

class VTST(nn.Module):
    def __init__(self, dataset="MNIST", latent_dim=128, num_classes=10, separate_body=False, beta=0.01, pretrained_qyx = None, accelerator="cpu", bound_qzx_var=False,
                 MLP_size=3, paper=None, simple_CNN=False, ViT_experiment=False, sample_experiment=False, train_samples=1, model_name_or_path='google/vit-base-patch16-224-in21k',
                 ResNet50_experiment=False, EfficientNet_experiment=False):
        super().__init__()
        self.latent_dim = latent_dim
        self.bound_qzx_var = bound_qzx_var
        self.train_samples = train_samples

        if dataset == "CIFAR10" or separate_body:
            self.separate_body = True
        else:
            self.separate_body = False
        if dataset == "CIFAR10" or self.separate_body:
            self.qzx_body = construct_ClassYEncoderBody(pretrained_model=pretrained_qyx, simple_CNN=simple_CNN,  ViT_experiment=ViT_experiment,dataset=dataset, model_name_or_path=model_name_or_path, ResNet50_experiment=ResNet50_experiment, EfficientNet_experiment=EfficientNet_experiment)
        self.qzx_model = construct_ClassYEncoder(dataset, self.latent_dim, simple_CNN=simple_CNN, num_layers=MLP_size, ViT_experiment=ViT_experiment, ResNet50_experiment=ResNet50_experiment, EfficientNet_experiment=EfficientNet_experiment)
        if self.bound_qzx_var:
            self.qzx_var = construct_EncoderVar(dataset, self.latent_dim, simple_CNN=simple_CNN, num_layers=MLP_size, ViT_experiment=ViT_experiment, ResNet50_experiment=ResNet50_experiment, EfficientNet_experiment=EfficientNet_experiment)

        self.pyz = construct_LabelDecoder(dataset, self.latent_dim, num_classes=num_classes)

        self.return_z = True

        self.num_classes = num_classes
        self.beta = beta
        if dataset.find("MNIST") == -1:
            self.input_h = 28
            self.input_w = 28
        elif dataset=="CIFAR10":
            self.input_h = 32
            self.input_w = 32  

        if accelerator == "gpu":
            self.device = "cuda:0"
        else:
            self.device = "cpu"  

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return eps * std + mu

    def encode_fixed_var(self, x, y=None):
        if self.separate_body:
            x = self.qzx_body(x)
        z_logvar = self.qzx_var(x)
        z_mean = self.qzx_model(x)
        return z_mean, z_logvar

    def encode(self, x, y=None):
        if self.separate_body:
            x = self.qzx_body(x)
        z_mean, z_logvar = self.qzx_model(x)
        return z_mean, z_logvar

    def decode(self, z, y):
        pyz = self.pyz(z)
        return pyz
    
    def forward(self, x, y=None):
        if self.bound_qzx_var:
            z_mean, z_logvar = self.encode_fixed_var(x, y)
        else:
            z_mean, z_logvar = self.encode(x, y)

        if self.training == True:
            if self.train_samples > 1:
                MC_logits = []
                for _ in range(self.train_samples):
                    z = self.reparameterize(z_mean, z_logvar)
                    pyz = self.decode(z, y)
                    MC_logits.append(pyz)

                pyz = torch.stack(MC_logits)
            else:
                z = self.reparameterize(z_mean, z_logvar)
                pyz = self.decode(z, y)
            return pyz, z_mean, z_logvar, z
        else:
            z = self.reparameterize(z_mean, z_logvar)
            pyz = self.decode(z, y)
            if self.return_z:
                return pyz, z_mean, z_logvar, z
            else:
                return pyz

    def forward_multisample(self, x, y=None, num_samples=10):
        #OBS: Outputs from this are already softmaxed!!!
        if self.bound_qzx_var:
            z_mean, z_logvar = self.encode_fixed_var(x, y)
        else:
            z_mean, z_logvar = self.encode(x, y)
        MC_probs = []
        for i in range(num_samples):
            z = self.reparameterize(z_mean, z_logvar)
            pyz = self.decode(z, y)
            MC_probs.append(F.softmax(pyz, dim=1))
        prob_tensor = torch.stack(MC_probs)
        preds = torch.mean(prob_tensor, dim=0)
        return preds
