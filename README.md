# Guide d'utilisation - Éditeur de bibliothèque iTunes

## 🎵 Gestionnaire de bibliothèque iTunes pour Linux

Cet outil vous permet de modifier facilement votre bibliothèque iTunes XML sur Linux Mint.

### 📋 Fichiers disponibles

- `itunes_library_manager.py` - Outil d'analyse et de statistiques
- `itunes_editor.py` - Outil de modification avancé
- `iTunes Music Library.xml` - Votre bibliothèque iTunes (92,065 pistes!)

### 🔧 Utilisation basique

#### 1. Analyser votre bibliothèque
```bash
python3 itunes_library_manager.py "iTunes Music Library.xml" --stats
```

#### 2. Rechercher des pistes
```bash
python3 itunes_library_manager.py "iTunes Music Library.xml" --search "Artist" "Beatles"
```

#### 3. Créer une sauvegarde
```bash
python3 itunes_editor.py "iTunes Music Library.xml" --backup
```

### 🛠️ Modifications courantes

#### Corriger les problèmes d'encodage
```bash
python3 itunes_editor.py "iTunes Music Library.xml" --backup --fix-encoding
```

#### Normaliser les noms d'artistes (supprimer espaces multiples)
```bash
python3 itunes_editor.py "iTunes Music Library.xml" --backup --normalize-artists
```

#### Remplacer du texte dans un champ
```bash
# Remplacer "The Beatles" par "Beatles" dans le champ Artist
python3 itunes_editor.py "iTunes Music Library.xml" --backup --replace "Artist" "The Beatles" "Beatles"
```

#### Mettre à jour les chemins de fichiers
```bash
# Changer E:/ vers /mnt/mybook/
python3 itunes_editor.py "iTunes Music Library.xml" --backup --update-paths "file://localhost/E:" "file://localhost/mnt/mybook"
```

#### Utiliser des expressions régulières
```bash
# Supprimer "(feat. ...)" des titres
python3 itunes_editor.py "iTunes Music Library.xml" --backup --regex-replace "Name" "\s*\(feat\..*?\)" ""
```

### 👀 Prévisualiser avant modification

```bash
# Voir quels titres contiennent "(feat."
python3 itunes_editor.py "iTunes Music Library.xml" --preview --replace "Name" "(feat." ""
```

### 📁 Champs modifiables

- `Name` - Titre de la chanson
- `Artist` - Artiste
- `Album` - Album
- `Album Artist` - Artiste de l'album
- `Genre` - Genre musical
- `Location` - Chemin du fichier
- `Comments` - Commentaires
- `Grouping` - Groupement

### ⚠️ Points importants

1. **Toujours créer une sauvegarde** avec `--backup`
2. **Tester avec `--preview`** avant les modifications importantes
3. **Le fichier original est en lecture seule** - modifications dans la copie locale
4. **Copier manuellement** vers `/mnt/mybook/Musiques/iTunes/` si nécessaire

### 🔄 Workflow recommandé

1. Créer une sauvegarde
2. Prévisualiser les changements
3. Appliquer les modifications
4. Vérifier le résultat
5. Copier vers l'emplacement original

### 💡 Exemples d'utilisation avancée

#### Nettoyer les titres avec feat.
```bash
python3 itunes_editor.py "iTunes Music Library.xml" --backup --regex-replace "Name" "\s*\(feat\..*?\)" ""
```

#### Standardiser les genres
```bash
python3 itunes_editor.py "iTunes Music Library.xml" --backup --replace "Genre" "Hip-Hop" "Hip Hop"
```

#### Corriger les chemins Windows vers Linux
```bash
python3 itunes_editor.py "iTunes Music Library.xml" --backup --regex-replace "Location" "file://localhost/E:/" "file://localhost/mnt/mybook/"
```

### 🆘 En cas de problème

- Restaurer depuis la sauvegarde : `cp "iTunes Music Library.xml.backup_YYYYMMDD_HHMMSS" "iTunes Music Library.xml"`
- Vérifier les permissions : `ls -la "iTunes Music Library.xml"`
- Tester avec un petit échantillon d'abord

### 📞 Support

Pour des modifications spécifiques ou des questions, décrivez ce que vous voulez modifier et je vous aiderai avec la commande exacte !