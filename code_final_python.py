# importation des modules
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
import chardet
import csv
import os
import matplotlib.dates as mdates
from IPython.display import Image
from scipy import stats

# on récupère les informations du dossier
dossier = './raw_data'
contenuDossier = os.listdir(dossier)
print(contenuDossier)
nombrePoints = 0
nomPoints = []
numeroPoints = []
# on parcours le dossier en recherchant les fichiers des points
for x in contenuDossier:
    if x.startswith('point'):
        nombrePoints += 1
        nomPoints.append(x)
        numeroPoints.append(x[5:7])
print(numeroPoints)
def read_csv (chemin_fichier):
    #Detecter separateur
    with open(chemin_fichier, 'r') as file:
        sniffer = csv.Sniffer()
        sample_data = file.read(1024)
        detecter_separateur = (sniffer.sniff(sample_data).delimiter)

    if "Titre" in open(chemin_fichier).readline():
        data_frame = pd.read_csv(chemin_fichier, sep=detecter_separateur, skiprows=1)
    else:
        data_frame = pd.read_csv(chemin_fichier, sep=detecter_separateur)

    return data_frame 


# on crée un dictionnaire avec toutes les informations pour chaque point et on met les dictionnaires dans une liste
data = []
for x in nomPoints :
    dico = {}
    # le numéro
    dico['numero'] = x[5:7]
    # le nom
    dico['nom'] = x
    # la date
    dico['date'] = x[8:18]
    # le chemin vers le dossier
    dico['chemin'] = dossier + '/' + x
    with open(dico['chemin'] + '/geometrie.txt', 'r') as fichier:
        lignes = fichier.readlines()
        # le nom du capteur
        dico['capteur'] = lignes[1][:4]
        # la profondeur du capteur
        if lignes[3] == '\n' :
            dico['profondeur'] = 0
        else : 
            dico['profondeur'] = lignes[3]
        # les profondeurs auquelles on fait les mesures
        dico['profondeurMesures'] = []
        profMes = lignes[5].split(';')
        for num in profMes :
            dico['profondeurMesures'].append(int(num))
    # on va ensuite mettre les dataframes dans le dictionnaire
    contenuDossierPoint = os.listdir(dico['chemin'])
    for x in contenuDossierPoint:
        # la pression
        if x.startswith('p') and x.endswith('.csv'):
            dico['pression'] = read_csv(dico['chemin'] + '/' + x)
        # la température
        if x.startswith('t') and x.endswith('.csv'):
            dico['temperature'] = read_csv(dico['chemin'] + '/' + x)
    # dans les configurations du capteur on va chercher les données
    chemin_etalonnage = 'configuration/pressure_sensors/P' + dico['capteur'][1:] +'.csv'
    if os.path.exists(chemin_etalonnage):
        with open(chemin_etalonnage) as fichier :
            lignes = fichier.readlines()
            for l in lignes :
                if l.startswith('Intercept') :
                    dico['intercept'] = float(l[10:-2])
                if l.startswith('dU/dH') :
                    dico['dU/dH'] = float(l[6:-2])
                if l.startswith('dU/dT') :
                    dico['dU/dT'] = float(l[6:-2]) 
    data.append(dico)



# Est ce que les fichiers peuvent être utilisés ?

### Est ce que nous avons les données de l'étalonnage du capteur ?
for x in data :
    if not 'intercept' in x.keys() :
        print('le point '+ x['numero'] + ' n\'a pas d\'étalonnage, il n\'est pas valide')
        data.remove(x)
### Est ce que nous avons des données pour le capteur de pression ?
for x in data :
    if x['pression'].empty :
        print('le point '+ x['numero'] + ' n\'a pas de données de pression, il n\'est pas valide')
        data.remove(x)
### On modifie les nom des colonnes du dataframe
# pour les températures
for x in data :
    # on supprime les colonnes qui ne servent à rien
    for i in x['temperature'].columns :
        if not( i.startswith('Date') or i.startswith('Temp')) :
            del x['temperature'][i]
    for i in x['pression'].columns :
        if not( i.startswith('Date') or i.startswith('Tension') or i.startswith('Temp')) :
            del x['pression'][i]
    # on renomme les colonnes
    profondeur = x['profondeurMesures']
    colonnesT = ['dates']
    for num in profondeur :
        colonnesT.append('Temp_profondeur_'+ str(num))
    x['temperature'].columns = colonnesT
    colonnesP = ['dates', 'tension', 'temperature_stream']
    x['pression'].columns = colonnesP
    

## Conversion de valeurs de tension a differance de charge
for point in data:
    k0 = float(point['intercept'])
    k1 = float(point['dU/dH'])
    k2 = float(point['dU/dT'])
    
    # Calcul de la colonne 'dH' en utilisant la formule H = 1/k1 * (U - k0 - k2 * T)
    U = point['pression']['tension'].astype(float)
    T = point['pression']['temperature_stream'].astype(float)
    point['pression']['dH'] = (1 / k1) * (U - k0 - k2 * T)


### On enlève les valeurs Nan
for x in data :
    x['temperature'] = x['temperature'].dropna(axis = 0, how = 'any')
    x['pression'] = x['pression'].dropna(axis = 0, how='any')
# Conversion dans le bon format date
for point in data:
    point['pression']['dates'] = pd.to_datetime(point['pression']['dates'], format='%m/%d/%y %I:%M:%S %p')
    point['temperature']['dates'] = pd.to_datetime(point['temperature']['dates'], format='%m/%d/%y %I:%M:%S %p')
data[0]['temperature'].head(5)
for x in data :
    # Traiter chaque colonne sauf la colonne des dates
    columns_to_processP = [col for col in x['pression'].columns if col != 'dates']
    columns_to_processT = [col for col in x['temperature'].columns if col != 'dates']
    # Créer un DataFrame vide pour stocker les données traitées
    x['pression2'] = x['pression'][['dates']].copy()
    x['temperature2'] = x['temperature'][['dates']].copy()
    # Boucler à travers chaque colonne à traiter
    for column_name in columns_to_processP :
        # Calculer le Z-score pour la colonne
        z_scores = np.abs(stats.zscore(x['pression'][column_name]))
        # Définir un seuil pour le Z-score (par exemple, 3)
        threshold = 3
        # Sélectionner les lignes avec des Z-scores inférieurs au seuil
        df_cleaned = x['pression'][z_scores < threshold] 
        # Copier les données traitées dans df_processed
        x['pression2'][column_name] = df_cleaned[column_name]
    # pareil pour les températures
    for column_name in columns_to_processT :
        # Calculer le Z-score pour la colonne
        z_scores = np.abs(stats.zscore(x['temperature'][column_name]))
        # Définir un seuil pour le Z-score (par exemple, 3)
        threshold = 3
        # Sélectionner les lignes avec des Z-scores inférieurs au seuil
        df_cleaned = x['temperature'][z_scores < threshold] 
        # Copier les données traitées dans df_processed
        x['temperature2'][column_name] = df_cleaned[column_name]
for x in data :
    x['temperature2'] = x['temperature2'].dropna(axis = 0, how = 'any')
    x['pression2'] = x['pression2'].dropna(axis = 0, how='any')
# on met à jour la date de début de la mesure, la date de fin et la période
for x in data :
    x['dateDebut'] = x['pression2']['dates'].iloc[0]
    x['dateFin'] = x['pression2']['dates'].iloc[x['pression2']['dates'].shape[0]-1]
    x['periode'] = x['dateFin'] - x['dateDebut']
### Est ce que nous avons au minimum 3 jours de données ?
for x in data :
    if int(str(x['periode'])[0]) <= 3 :
        print('le point ' + x['numero'] + ' n\'est pas valide car sa période est de seulement ' + str(x['periode'])[0] +' jours')
        data.remove(x)


### Création du fichier `info.txt`
# Ouvrez un fichier en mode écriture ('w')
for x in data :
    if os.path.exists(x['chemin'] + '/point' + x['numero'] + '_info.txt') :
        os.remove(x['chemin'] + '/point' + x['numero'] + '_info.txt')
    with open(x['chemin'] + '/point' + x['numero'] + '_info.txt', 'w') as fichier:
        # Parcourez le dictionnaire et écrivez les données dans le fichier
        fichier.write('Point_Name,Point' + x['numero'] + '\n')
        fichier.write('P_Sensor_Name,' + x['capteur'] + '\n')
        fichier.write('Implantation_Date,' + x['date'] + '\n')
        fichier.write('Meas_date,' + str(x['dateDebut']) + '\n')
        fichier.write('River_Deb,' '\n') 
        fichier.write('Delta_h,' + '\n')
        fichier.write('Periode,' + str(x['periode']) + '\n')










# Traitement du signal de temperature
from scipy import signal

# Butterworth filter method

T_s_C = data[1]['pression2'][['temperature_stream','dates']]

data_to_filter = T_s_C['temperature_stream']

order = 4
cutoff_freq = 2*(15/60/48)
b, a = signal.butter(order, cutoff_freq, 'lowpass')
filtered_T = signal.lfilter(b, a, data_to_filter)

filtered_T_s_C = pd.DataFrame({'filtered_temperature_stream': filtered_T, 'dates': T_s_C['dates']})


import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(T_s_C["dates"], T_s_C["temperature_stream"], color="red", label="T_s_C_original", s=5)
ax.plot(filtered_T_s_C["dates"], filtered_T_s_C["filtered_temperature_stream"], color="blue", label="filtered_T_s_C")
ax.set_xlabel("Date")
ax.set_ylabel("temperature_T_s_C")
ax.set_title("Time Series Comparison ")
ax.legend()

plt.tight_layout()
plt.show()
# Butterworth filter method

T_s_C = data[1]['pression2'][['temperature_stream','dates']]

data_to_filter = T_s_C['temperature_stream']

order = 4
cutoff_freq = 2*(15/60/48)
b, a = signal.butter(order, cutoff_freq, 'lowpass')
filtered_T = signal.lfilter(b, a, data_to_filter)

filtered_T_s_C = pd.DataFrame({'filtered_temperature_stream': filtered_T, 'dates': T_s_C['dates']})


import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(T_s_C["dates"], T_s_C["temperature_stream"], color="red", label="T_s_C_original", s=5)
ax.plot(filtered_T_s_C["dates"], filtered_T_s_C["filtered_temperature_stream"], color="blue", label="filtered_T_s_C")
ax.set_xlabel("Date")
ax.set_ylabel("temperature_T_s_C")
ax.set_title("Time Series Comparison ")
ax.legend()

plt.tight_layout()
plt.show()
# Butterworth two-way-filter method

forward_filtered_signal = signal.lfilter(b, a, data_to_filter)

reversed_signal = data_to_filter[::-1]
backward_filtered_signal = signal.lfilter(b, a, reversed_signal)
backward_filtered_signal = backward_filtered_signal[::-1]

filtered_T_s_C_forward = pd.DataFrame({'filtered_temperature_stream': forward_filtered_signal, 'dates': T_s_C['dates']})
filtered_T_s_C_backward = pd.DataFrame({'filtered_temperature_stream': backward_filtered_signal, 'dates': T_s_C['dates']})

fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(T_s_C["dates"], T_s_C["temperature_stream"], color="red", label="T_s_C_original", s=5)
ax.plot(filtered_T_s_C_forward["dates"], filtered_T_s_C_forward["filtered_temperature_stream"], color="blue", label="filtered_T_s_C_forward")
ax.set_xlabel("Date")
ax.set_ylabel("temperature_T_s_C_forward")
ax.set_title("Time Series Comparison " )
ax.legend()

fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(T_s_C["dates"], T_s_C["temperature_stream"], color="red", label="T_s_C_original", s=5)
ax.plot(filtered_T_s_C_backward["dates"], filtered_T_s_C_backward["filtered_temperature_stream"], color="blue", label="filtered_T_s_C_backward")
ax.set_xlabel("Date")
ax.set_ylabel("temperature_T_s_C_backward")
ax.set_title("Time Series Comparison Point '\n'")
ax.legend()

plt.tight_layout()
plt.show()
# Combination of two-way-filtered signal with weight fonction

L = len(data_to_filter)
weight = np.zeros(L)
combined_filtered_signal = np.zeros(L)

a = 1.0 / L
for i in range(L):
    weight[i] = i * a

for i in range(L):
    combined_filtered_signal[i] = forward_filtered_signal[i] * weight[i] + backward_filtered_signal[i] * (1-weight[i])

combined_filtered_T_s_C = pd.DataFrame({'combined_filtered_temperature_stream': combined_filtered_signal, 'dates': T_s_C['dates']})
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(T_s_C["dates"], T_s_C["temperature_stream"], color="red", label="T_s_C_original", s=5)
ax.plot(combined_filtered_T_s_C["dates"], combined_filtered_T_s_C["combined_filtered_temperature_stream"], color="blue", label="combined_filtered_T_s_C")
ax.set_xlabel("Date")
ax.set_ylabel("temperature_T_s_C")
ax.set_title("Time Series Comparison")
ax.legend()

plt.tight_layout()
plt.show()
# Regenerate dH with the filtered temperature
filtered_dH = pd.DataFrame()

k0 = float(data[2]['intercept'])
k1 = float(data[2]['dU/dH'])
k2 = float(data[2]['dU/dT'])

U = data[2]['pression']['tension'].astype(float)
T = combined_filtered_T_s_C["combined_filtered_temperature_stream"].astype(float)
#point['pression']['dH'] = (1 / k1) * (U - k0 - k2 * T)

# filtered_dH['filtered_dH'] = (1 / k1) * (capteur_riviere['tension_V'].astype(float) - k0 ）
filtered_dH['filtered_dH'] = (1 / k1) * (U - k0 - k2 * T)
filtered_dH['dates'] = T_s_C['dates']

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(data[2]['pression2']["dates"], data[2]['pression2']["dH"], color="red", label="dH (Cleaned Data)")
ax.plot(filtered_dH["dates"], filtered_dH["filtered_dH"], color="blue", label="filtered_dH")
ax.set_xlabel("Date")
ax.set_ylabel("dH")
ax.set_title("Time Series Comparison")
ax.legend()

plt.tight_layout()
plt.show()

