import torch
import torch.nn as nn
import torch.nn.functional as F

def local_kernel(u, v):
    dist = torch.norm(u - v, p=2, dim=2)
    hat = torch.clamp(1. - dist**2, min=0.)
    return hat

class KernelLayer(nn.Module):
    def __init__(self, n_in, n_hid, n_dim, lambda_s, lambda_2, activation=nn.Sigmoid()):
      super().__init__()
      self.W = nn.Parameter(torch.randn(n_in, n_hid))
      self.u = nn.Parameter(torch.randn(n_in, 1, n_dim))
      self.v = nn.Parameter(torch.randn(1, n_hid, n_dim))
      self.b = nn.Parameter(torch.randn(n_hid))

      self.lambda_s = lambda_s
      self.lambda_2 = lambda_2

      nn.init.xavier_uniform_(self.W, gain=torch.nn.init.calculate_gain("relu"))
      nn.init.xavier_uniform_(self.u, gain=torch.nn.init.calculate_gain("relu"))
      nn.init.xavier_uniform_(self.v, gain=torch.nn.init.calculate_gain("relu"))
      nn.init.zeros_(self.b)
      self.activation = activation

    def forward(self, x):
      w_hat = local_kernel(self.u, self.v)
    
      sparse_reg = torch.nn.functional.mse_loss(w_hat, torch.zeros_like(w_hat))
      sparse_reg_term = self.lambda_s * sparse_reg
      
      l2_reg = torch.nn.functional.mse_loss(self.W, torch.zeros_like(self.W))
      l2_reg_term = self.lambda_2 * l2_reg

      W_eff = self.W * w_hat  # Local kernelised weight matrix
      y = torch.matmul(x, W_eff) + self.b
      y = self.activation(y)

      return y, sparse_reg_term + l2_reg_term

class KernelNet(nn.Module):
    def __init__(self, n_u, n_hid, n_dim, lambda_s, lambda_2):
        super().__init__()
        # First hidden layer
        self.encoder1 = KernelLayer(n_u, n_hid, n_dim, lambda_s, lambda_2)
        # Latent Space
        self.encoder2 = KernelLayer(n_hid, n_hid, n_dim, lambda_s, lambda_2)
        # Output layer
        self.decoder1 = KernelLayer(n_hid, n_u, n_dim, lambda_s, lambda_2, activation=nn.Identity())
        
        self.dropout = nn.Dropout(0.33)

    def forward(self, x):
        total_reg = None
        
        # First layer
        x, reg1 = self.encoder1(x)
        x = self.dropout(x)
        
        # Second layer
        latent, reg2 = self.encoder2(x)
        x = self.dropout(latent)
        
        # Output layer
        x, reg3 = self.decoder1(x)
        
        # Summing regularization terms
        total_reg = reg1 + reg2 + reg3

        return x, latent, total_reg


class CompleteNet(nn.Module):
    def __init__(self, kernel_net, n_m, gk_size, dot_scale):
      super().__init__()
      self.gk_size = gk_size
      self.dot_scale = dot_scale
      self.local_kernel_net = kernel_net
      self.conv_kernel = torch.nn.Parameter(torch.randn(n_m, gk_size**2) * 0.1)
      nn.init.xavier_uniform_(self.conv_kernel, gain=torch.nn.init.calculate_gain("relu"))
      

    def forward(self, x, x_local):
      gk = self.global_kernel(x_local, self.gk_size, self.dot_scale)
      x = self.global_conv(x, gk)
      x, latent, global_reg_loss = self.local_kernel_net(x)
      return x, latent, global_reg_loss

    def global_kernel(self, input, gk_size, dot_scale):
      avg_pooling = torch.mean(input, dim=1)  # Item (axis=1) based average pooling
      avg_pooling = avg_pooling.view(1, -1)

      gk = torch.matmul(avg_pooling, self.conv_kernel) * dot_scale  # Scaled dot product
      gk = gk.view(1, 1, gk_size, gk_size)

      return gk

    def global_conv(self, input, W):
      input = input.unsqueeze(0).unsqueeze(0)
      conv2d = nn.LeakyReLU()(F.conv2d(input, W, stride=1, padding=1))
      return conv2d.squeeze(0).squeeze(0)

class Loss(nn.Module):
    def forward(self, pred_p, reg_loss, train_m, train_r):
      # L2 loss
      diff = train_m * (train_r - pred_p)
      sqE = torch.nn.functional.mse_loss(diff, torch.zeros_like(diff))
      loss_p = sqE + reg_loss
      return loss_p