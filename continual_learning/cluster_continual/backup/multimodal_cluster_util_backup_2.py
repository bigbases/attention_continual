from torch.utils.data import Dataset, DataLoader , TensorDataset
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import os 
from sklearn.metrics import mean_absolute_error , mean_absolute_percentage_error , mean_squared_error
from sklearn.model_selection import train_test_split
import random 
#Cluster ===============================
from sklearn.cluster import AgglomerativeClustering
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
from sklearn.mixture import GaussianMixture

from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture
from torch.utils.data import ConcatDataset
import copy 
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from cosineKmeans import CosineKMeans , EuclideanKMeans


device = 'cuda'

class Multimodal_utils():
    
    def __init__(self,cluster_n = 4,memory_size = 10000,modal_number = 9) -> None:
        self.clustered_data = []
        self.replay_feature = []
        self.replay_label = []
        self.vali_feature = []
        self.vali_label = []
        
        self.n_cluster = cluster_n
        self.memory_size = memory_size
        self.modal_number = modal_number
        
        self.task_num = 1
        

    def Train(self,model, optimizer, loss_fn, train_loaders, vali_loader, epochs, early_stopping):
        
        for epoch in range(epochs):
            model.train()
            loss_preds = []

            for batch in zip(*train_loaders):
                # print([len(b[0]) for b in batch])
                features = torch.cat([b[0] for b in batch], dim=0)  # 모든 features 합치기
                labels = torch.cat([b[1] for b in batch], dim=0)  # 모든 labels 합치기
                # print(features.shape)
                # 훈련 부분
                # for  (features1, label1) ,(features2, label2) , (features3, label3) , (features4, label4)  in zip(train_loaders[0],train_loaders[1],train_loaders[2],train_loaders[3]):
                # # for  (features1, label1) ,(features2, label2)   in zip(train_loaders[0],train_loaders[1]):

                #     features = torch.cat((features1, features2, features3, features4), dim=0)
                #     label = torch.cat((label1, label2, label3, label4), dim=0)
                
                # features = torch.cat((features1, features2 ), dim=0)
                # label = torch.cat((label1, label2), dim=0)
                # print(features.shape)
                # print(label.shape)
                if features.shape[0] <= 1 :
                    # print('사이즈가 작아 break 합니다. ')
                    continue

                features, labels = features.to(device), labels.to(device)
                y_pred, att = model(features)
                optimizer.zero_grad()
                
                loss_pred = loss_fn(y_pred, labels)
                loss_preds.append(loss_pred.item())
                loss_pred.backward()
                optimizer.step()

            # 에포크의 평균 손실 계산
            avg_loss = sum(loss_preds) / len(loss_preds)

            # 검증 부분
            # if vali_loader is not None:    
            model.eval()
            val_loss = 0
            sha= 0 
            with torch.no_grad():
                for features, label in vali_loader:
                    features, label = features.to(device), label.to(device)
                    y_pred, _ = model(features)
                    val_loss += loss_fn(y_pred, label).item()
                    
                    sha += features.shape[0]
            val_loss /= sha

            #val_loss /= len(vali_loader)

            # 조기 종료 체크
            if early_stopping(val_loss, model):
                print(f'Early stopping at epoch {epoch}')
                break
            if epoch % 10 == 0 :
                print(val_loss)
                pass
        return model , avg_loss
    
    
    
    def Train2(self,model, optimizer, loss_fn, train_loaders, vali_loader, epochs, early_stopping):
        
        for epoch in range(epochs):
            model.train()
            loss_preds = []

            for batch in zip(*train_loaders):
                # print([len(b[0]) for b in batch])
                features = torch.cat([b[0] for b in batch], dim=0)  # 모든 features 합치기
                labels = torch.cat([b[1] for b in batch], dim=0)  # 모든 labels 합치기
                loss_total = 0
                for b in batch:
                    f = b[0].to(device)
                    l = b[1].to(device)
                    
                    y_pred, att = model(f)
                    optimizer.zero_grad()
                    
                    loss_pred = loss_fn(y_pred, l)
                    loss_total += loss_pred
                
                # print(loss_total)
                loss_preds.append(loss_pred.item())
                loss_total.backward()
                optimizer.step()

                

            # 에포크의 평균 손실 계산
            avg_loss = sum(loss_preds) / len(loss_preds)

            # 검증 부분
            # if vali_loader is not None:    
            model.eval()
            val_loss = 0
            sha= 0 
            with torch.no_grad():
                for features, label in vali_loader:
                    features, label = features.to(device), label.to(device)
                    y_pred, _ = model(features)
                    val_loss += loss_fn(y_pred, label).item()
                    
                    sha += features.shape[0]
            val_loss /= sha

            #val_loss /= len(vali_loader)

            # 조기 종료 체크
            if early_stopping(val_loss, model):
                print(f'Early stopping at epoch {epoch}')
                break
            if epoch % 10 == 0 :
                print(val_loss)
                pass
        return model , avg_loss




    def meta_Train(self,model,optimizer,loss_fn,dataloader):
        feature_lst = []
        label_lst = []
        meta_lst = []
        att_lst = []
        loss_lst = []
        model.eval()
        for batch, (features, label) in enumerate(dataloader):
            model.zero_grad()
            optimizer.zero_grad()
            
            feature_lst.extend(features)
            label_lst.extend(label)
            

            features, label = features.to(device), label.to(device) 


            y_pred ,att = model(features)
            # print(att.shape)
            # exit()
            att_lst.extend(att)
            
            #print(list(tmp_model.parameters())[0].grad[0])
            loss_pred = loss_fn(y_pred , label)


            loss_pred.backward()

            loss_lst.append(loss_pred.item())
            # meta_lst.append(grad)

        feature_lst = np.array([feature.detach().cpu().numpy() for feature in feature_lst])
        label_lst = np.array([label.detach().cpu().numpy() for label in label_lst])

        att_lst =np.array([att.detach().cpu().numpy() for att in att_lst])
        att_lst = att_lst.reshape(-1,self.modal_number)
        
        return feature_lst,label_lst, att_lst


    def cluster_based_replay_loader(self):

        tmp_feature = []
        tmp_label = []
        batch_size = 128
        replay_loaders = []
        # replay_feature_tmp = replay_feature[0]
        # replay_label_tmp = replay_label[0]
        total_size = sum([len(f) for f in self.replay_label])
        print('Feature size : ',[len(f) for f in self.replay_feature])
        for features, labels in zip(self.replay_feature,self.replay_label):
            # print('====='*20)
            # print(len(features))
            # print(len(labels))
            # print(int(batch_size*(len(features)/total_size)))
            replay_dataset = TensorDataset(torch.tensor(features), torch.tensor(labels))
            cluster_batch_size = batch_size*(len(features)/total_size)
            if int(cluster_batch_size) == 0  :
                continue
            #temp
            cluster_batch_size = 32
            #temp
            replay_dataloader = DataLoader(replay_dataset, batch_size=int(cluster_batch_size), shuffle=True)
                
            replay_loaders.append(replay_dataloader)
        
        tmp_feature = []
        tmp_label = []
            
        for features, labels in zip(self.vali_feature,self.vali_label):

            tmp_feature.extend(features)
            tmp_label.extend(labels) 
        vali_dataset = TensorDataset(torch.tensor(tmp_feature), torch.tensor(tmp_label))

        vali_dataloader = DataLoader(vali_dataset, batch_size=64, shuffle=True)
        
        
        
        return replay_loaders ,vali_dataloader






    def allocate_memory(self,memory_size,replay,new,n_cluster):

        K = memory_size // (self.task_num + 1)
        self.task_num+=1
        
        replay_clusters, replay_memory_feature, replay_memory_label = replay
        new_clusters, new_memory_feature, new_memory_label = new
        
        if replay_clusters is not None:
            replay_clustered_indices = []
            for i in range(n_cluster):
                indices = np.where(replay_clusters == i)[0]
                np.random.shuffle(indices) # 섞여도 됨. 
                replay_clustered_indices.append(indices)
            
            
            total_size = sum([len(cluster) for cluster in replay_clustered_indices])

            replay_cluster_memory = [ int((memory_size-K)*(len(cluster)/total_size)) for cluster in replay_clustered_indices]

            surplus = (memory_size - K ) - sum([cluster_size for cluster_size in replay_cluster_memory])
            for i in range(surplus):
                replay_cluster_memory[i]+=1
        
        # Replay Dataset:
        # New Dataset
        
        new_clustered_indices = []
        print('new_clusters shape',new_clusters.shape)
        for i in range(n_cluster):
            indices = np.where(new_clusters == i)[0]
            np.random.shuffle(indices) # 섞여도 됨 .
            new_clustered_indices.append(indices)
        
        total_size = sum([len(cluster) for cluster in new_clustered_indices])
        new_cluster_memory = [ int( K * (len(cluster)/total_size)) for cluster in new_clustered_indices]
        surplus = K - sum([cluster_size for cluster_size in new_cluster_memory])
        for i in range(surplus):
            new_cluster_memory[i]+=1


        
        tmp_feature = []
        tmp_label = []

        # Replay 데이터셋 처리
        if replay_clusters is not None:
            for cluster_idx, (replay_memory_size , new_memory_size) in enumerate(zip(replay_cluster_memory,new_cluster_memory)):
                # 클러스터별 샘플 선택
                replay_selected_indices = replay_clustered_indices[cluster_idx][:replay_memory_size]
                new_selected_indices = new_clustered_indices[cluster_idx][:new_memory_size]
                # 선택된 샘플 추가
                t_feature = []
                t_feature.extend(replay_memory_feature[replay_selected_indices])
                t_feature.extend(new_memory_feature[new_selected_indices])
                t_label = []
                t_label.extend(replay_memory_label[replay_selected_indices])
                t_label.extend(new_memory_label[new_selected_indices])
                tmp_feature.append(t_feature)
                tmp_label.append(t_label)
                
            print('replay clusted indices size ',replay_cluster_memory)
        else:
            
        # New 데이터셋 처리
            for cluster_idx, memory_size in enumerate(new_cluster_memory):
                # 클러스터별 샘플 선택
                selected_indices = new_clustered_indices[cluster_idx][:memory_size]
                # 선택된 샘플 추가

                tmp_feature.append(new_memory_feature[selected_indices])
                tmp_label.append(new_memory_label[selected_indices])

        
        print('new clusted indices size ',new_cluster_memory)

        
        if len(self.replay_feature)<1:

            self.replay_feature.extend(tmp_feature)
            self.replay_label.extend(tmp_label)
            # print([len(f) for f in tmp_feature])
            # print([len(f) for f in replay_feature])
            
        else:
            

            for idx in range(len(self.replay_feature)):
                        
                self.replay_feature[idx] = tmp_feature[idx]
                self.replay_label[idx] = tmp_label[idx]
            # print([len(f) for f in tmp_feature])
            # print([len(f) for f in replay_feature])
        
        
        
        vali_sizes = [int(K*0.1) for i in range(len(self.vali_feature))]
            
        for idx, (features, labels) in enumerate(zip(self.vali_feature,self.vali_label)):
            
            self.vali_feature[idx] = features[:vali_sizes[idx]]
            self.vali_label[idx] = labels[:vali_sizes[idx]]
            
        vali_size = int(K*0.1)
        
        indices = list(range(len(new_memory_feature)))
        selected_features = new_memory_feature[indices[-vali_size:]]
        selected_labels = new_memory_label[indices[-vali_size:]]
        self.vali_feature.append(selected_features)
        self.vali_label.append(selected_labels)
        
        return 




    clustered_data = []
    replay_feature = []
    replay_label = []
    vali_feature = []
    vali_label = []

    def make_replay_loader_before(self):
        # 데이터 선택 및 셔플링

        tmp_feature = []
        tmp_label = []
        
        for features, labels in zip(self.replay_feature,self.replay_label):

            tmp_feature.extend(features)
            tmp_label.extend(labels) 
        replay_train_dataset = TensorDataset(torch.tensor(tmp_feature), torch.tensor(tmp_label))


        tmp_feature = []
        tmp_label = []
        
        for features, labels in zip(self.vali_feature,self.vali_label):

            tmp_feature.extend(features)
            tmp_label.extend(labels) 
        replay_vali_dataset = TensorDataset(torch.tensor(tmp_feature), torch.tensor(tmp_label))
        
        return replay_train_dataset, replay_vali_dataset




    def Start_meta_solution(self,model,loss_fn,optimizer,new_dataset):
        
        
        
        if len(self.replay_feature)>0:
            
            replay_train_dataset, replay_vali_dataset = self.make_replay_loader_before()
            meta_loader_replay  = DataLoader(replay_train_dataset, batch_size=512, shuffle=True)
            meta_loader_new =  DataLoader(new_dataset, batch_size=512, shuffle=False)
            
            replay_feature_lst,replay_label_lst,replay_att_lst = self.meta_Train(model,optimizer,loss_fn,meta_loader_replay)
            new_feature_lst,new_label_lst,new_att_lst = self.meta_Train(model,optimizer,loss_fn,meta_loader_new)
            
            clustering_model = EuclideanKMeans(n_clusters = self.n_cluster, max_iter = 1000)
            replay_clusters = clustering_model.fit_predict(replay_att_lst)
            new_clusters = clustering_model.predict(new_att_lst)
        else:
            meta_loader_new =  DataLoader(new_dataset, batch_size=512, shuffle=False)
            new_feature_lst,new_label_lst,  new_att_lst   = self.meta_Train(model,optimizer,loss_fn,meta_loader_new)
            clustering_model = EuclideanKMeans(n_clusters = self.n_cluster, max_iter = 1000)

            new_clusters = clustering_model.fit_predict(new_att_lst)

            replay_clusters,replay_feature_lst,replay_label_lst = None,None,None

        replay, new = (replay_clusters,replay_feature_lst,replay_label_lst),(new_clusters, new_feature_lst, new_label_lst)
        self.allocate_memory(self.memory_size,replay, new,self.n_cluster)
        
            
            
        replay_train_loader ,replay_vali_loader= self.cluster_based_replay_loader()
        
        print('Train : 현재 Memory Data : ',sum([len(feature) for feature in self.replay_feature]))
        print('Vali : 현재 Memory Data : ',sum([len(feature) for feature in self.vali_feature]))
        
        
        return replay_train_loader,replay_vali_loader






#=================#=================#=================#=================#=================#=================#=================

