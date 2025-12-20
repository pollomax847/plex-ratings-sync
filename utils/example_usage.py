#!/usr/bin/env python3
"""
Exemple d'utilisation de Plex Ratings Sync
Version générique pour partage sur GitHub
"""

import sys
from pathlib import Path

# Exemple d'utilisation basique
def exemple_simulation():
    """Mode simulation - recommandé pour commencer"""
    print("=== MODE SIMULATION ===")
    print("Commande: python3 plex_ratings_sync.py --auto-find-db")
    print("- Analyse la base Plex")
    print("- Détecte les fichiers 1⭐ et 2⭐")
    print("- Aucune suppression réelle")
    print()

def exemple_suppression():
    """Mode suppression réelle avec sauvegarde"""
    print("=== MODE SUPPRESSION RÉELLE ===")
    print("Commande: python3 plex_ratings_sync.py --auto-find-db --delete --backup ./backup")
    print("- Supprime les fichiers 1⭐")
    print("- Identifie les fichiers 2⭐ avec songrec")
    print("- Sauvegarde dans ./backup avant suppression")
    print()

def exemple_albums_artistes():
    """Suppression d'albums et artistes entiers"""
    print("=== SUPPRESSION ALBUMS/ARTISTES ===")
    print("Commande: python3 plex_ratings_sync.py --auto-find-db --delete --delete-albums --delete-artists")
    print("- Supprime les albums notés 1⭐")
    print("- Supprime les artistes notés 1⭐")
    print("- Conserve les fichiers individuels 3-5⭐")
    print()

def exemple_nettoyage():
    """Nettoyage des anciens logs"""
    print("=== NETTOYAGE LOGS ===")
    print("Commande: python3 plex_ratings_sync.py --auto-find-db --cleanup-logs 30")
    print("- Supprime les logs de plus de 30 jours")
    print("- Nettoie les rapports de suppression anciens")
    print()

def exemple_stats():
    """Affichage des statistiques"""
    print("=== STATISTIQUES ===")
    print("Commande: python3 plex_ratings_sync.py --auto-find-db --stats")
    print("- Affiche la répartition des ratings")
    print("- Nombre de fichiers par étoile")
    print("- Albums et artistes avec ratings")
    print()

if __name__ == "__main__":
    print("EXEMPLES D'UTILISATION - PLEX RATINGS SYNC")
    print("=" * 50)
    print()

    exemple_simulation()
    exemple_suppression()
    exemple_albums_artistes()
    exemple_nettoyage()
    exemple_stats()

    print("CONSEILS DE SÉCURITÉ:")
    print("- Toujours tester en --auto-find-db d'abord (simulation)")
    print("- Utiliser --backup pour sauvegarder avant suppression")
    print("- Vérifier les logs après chaque exécution")
    print("- Faire des sauvegardes régulières de votre base Plex")