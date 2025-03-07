from train_cbf_service import GlocalArchitecture
from time import time
import numpy as np
import torch


class Glocal:
    def __init__(self, n_u, n_m):
        n_hid = 500 # size of hidden layers
        n_dim = 5 # inner AE embedding size
        n_layers = 2 # number of hidden layers
        gk_size = 3 # width=height of kernel for convolution

        # Hyperparameters to tune for specific case
        self.max_epoch_p = 30 # max number of epochs for pretraining
        self.max_epoch_f = 50 # max number of epochs for finetuning
        self.patience_p = 5 # number of consecutive rounds of early stopping condition before actual stop for pretraining
        self.patience_f = 10 # and finetuning
        self.tol_p = 1e-4 # minimum threshold for the difference between consecutive values of train rmse, used for early stopping, for pretraining
        self.tol_f = 1e-5 # and finetuning
        lambda_2 = 20. # regularisation of number or parameters
        lambda_s = 0.006 # regularisation of sparsity of the final matrix
        dot_scale = 1 
        self.current_latent = None

        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.kernel_net = GlocalArchitecture.KernelNet(n_u, n_hid, n_dim, lambda_s, lambda_2).double().to(self.device)
        self.complete_net = GlocalArchitecture.CompleteNet(self.kernel_net, n_m, gk_size, dot_scale).double().to(self.device)
        self.loss_fn = GlocalArchitecture.Loss().to(self.device)
        self.optimizer = torch.optim.AdamW(self.complete_net.local_kernel_net.parameters(), lr=0.001)

    def pre_train(self, train_r, train_m):
        """
        Pre-trains the local kernel network using all available data.
        """
        self.time_cumulative = 0
        self.tic = time()
        
        def closure():
            self.optimizer.zero_grad()
            x = torch.Tensor(train_r).double().to(self.device)
            m = torch.Tensor(train_m).double().to(self.device)
            self.complete_net.local_kernel_net.train()
            pred, _, reg = self.complete_net.local_kernel_net(x)
            loss = self.loss_fn(pred, reg, m, x)
            loss.backward()
            return loss
        
        last_rmse = np.inf
        counter = 0
        
        for i in range(self.max_epoch_p):
            self.optimizer.step(closure)
            self.complete_net.local_kernel_net.eval()
            t = time() - self.tic
            self.time_cumulative += t

            self.pre, _ , _= self.complete_net.local_kernel_net(torch.Tensor(train_r).double().to(self.device))
            self.pre = self.pre.float().cpu().detach().numpy()
            
            error_train = (train_m * (np.clip(self.pre, 1., 5.) - train_r) ** 2).sum() / train_m.sum()
            train_rmse = np.sqrt(error_train)

            if last_rmse - train_rmse < self.tol_p:
                counter += 1
            else:
                counter = 0
            
            last_rmse = train_rmse

            if self.patience_p == counter:
                print('.-^-._' * 12)
                print('PRE-TRAINING')
                print('Epoch:', i + 1, 'train rmse:', train_rmse)
                print('Time:', t, 'seconds')
                print('Time cumulative:', self.time_cumulative, 'seconds')
                print('.-^-._' * 12)
                break

            if i % 50 != 0:
                continue
            print('.-^-._' * 12)
            print('PRE-TRAINING')
            print('Epoch:', i, 'train rmse:', train_rmse)
            print('Time:', t, 'seconds')
            print('Time cumulative:', self.time_cumulative, 'seconds')
            print('.-^-._' * 12)

        # Final forward pass without gradients to capture last latent vectors
        with torch.no_grad():
            self.complete_net.local_kernel_net.eval()
            x = torch.Tensor(train_r).double().to(self.device)
            _, latent, _ = self.complete_net.local_kernel_net(x)
            self.current_latent = latent.cpu().numpy()

    def finetune(self, train_r, train_m):
        train_r_local = np.clip(self.pre, 1., 5.)
        optimizer = torch.optim.AdamW(self.complete_net.parameters(), lr=0.001)

        def closure():
            optimizer.zero_grad()
            x = torch.Tensor(train_r).double().to(self.device)
            x_local = torch.Tensor(train_r_local).double().to(self.device)
            m = torch.Tensor(train_m).double().to(self.device)
            self.complete_net.train()
            pred, latent, reg = self.complete_net(x, x_local)
            loss = self.loss_fn(pred, reg, m, x)
            loss.backward()
            return loss

        last_rmse = np.inf
        counter = 0
        final_train_rmse, final_train_mae = None, None

        for i in range(self.max_epoch_f):
            optimizer.step(closure)
            self.complete_net.eval()

            t = time() - self.tic
            self.time_cumulative += t

            self.pre, _, _ = self.complete_net(torch.Tensor(train_r).double().to(self.device), 
                                            torch.Tensor(train_r_local).double().to(self.device))
            
            self.pre = self.pre.float().cpu().detach().numpy()

            error_train = (train_m * (np.clip(self.pre, 1., 5.) - train_r) ** 2).sum() / train_m.sum()  # train error
            train_rmse = np.sqrt(error_train)
            train_mae = (train_m * np.abs(np.clip(self.pre, 1., 5.) - train_r)).sum() / train_m.sum()

            final_train_rmse, final_train_mae = train_rmse, train_mae

            if last_rmse - train_rmse < self.tol_f:
                counter += 1
            else:
                counter = 0

            last_rmse = train_rmse

            if self.patience_f == counter:
                break

            if i % 50 == 0:
                print('.-^-._' * 12)
                print('FINE-TUNING')
                print('Epoch:', i, 'train rmse:', train_rmse, 'train mae:', train_mae)
                print('Time:', t, 'seconds')
                print('Time cumulative:', self.time_cumulative, 'seconds')
                print('.-^-._' * 12)

        # Ensure final values are always printed
        print('.-^-._' * 12)
        print('FINAL FINE-TUNING RESULTS')
        print('Final Epoch:', i + 1)
        print('Final train rmse:', final_train_rmse)
        print('Final train mae:', final_train_mae)
        print('Total Time:', self.time_cumulative, 'seconds')
        print('.-^-._' * 12)
        
        with torch.no_grad():
            self.complete_net.eval()
            x = torch.Tensor(train_r).double().to(self.device)
            _, latent, _ = self.complete_net.local_kernel_net(x)
            self.current_latent = latent.cpu().numpy()

    def get_latent(self):
        return self.current_latent