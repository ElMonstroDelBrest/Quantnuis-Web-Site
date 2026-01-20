#!/usr/bin/env python3
"""
================================================================================
                    FONCTIONS D'AFFICHAGE
================================================================================

Fonctions utilitaires pour l'affichage formaté dans le terminal.

Usage:
    from shared import print_header, print_success, print_info
    
    print_header("Ma Section")
    print_success("Opération réussie")
    print_info("Information importante")

================================================================================
"""

from .colors import Colors


def print_header(title: str, width: int = 50):
    """
    Affiche un en-tête de section formaté.
    
    Résultat visuel :
    ──────────────────────────────────────────────────
      TITRE DE LA SECTION
    ──────────────────────────────────────────────────
    
    Paramètres:
        title (str): Le titre à afficher (sera converti en MAJUSCULES)
        width (int): Largeur de l'en-tête (défaut: 50)
    """
    print()
    print(f"{Colors.CYAN}{Colors.BOLD}{'─' * width}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}  {title.upper()}{Colors.END}")
    print(f"{Colors.CYAN}{'─' * width}{Colors.END}")


def print_success(msg: str):
    """
    Affiche un message de succès avec le préfixe [OK] en vert.
    
    Résultat : [OK] Message de succès
    
    Paramètres:
        msg (str): Le message à afficher
    """
    print(f"{Colors.GREEN}[OK]{Colors.END} {msg}")


def print_info(msg: str):
    """
    Affiche un message d'information avec le préfixe [i] en cyan.
    
    Résultat : [i] Message informatif
    
    Paramètres:
        msg (str): Le message à afficher
    """
    print(f"{Colors.CYAN}[i]{Colors.END} {msg}")


def print_warning(msg: str):
    """
    Affiche un avertissement avec le préfixe [!] en jaune.
    
    Résultat : [!] Message d'avertissement
    
    Paramètres:
        msg (str): Le message à afficher
    """
    print(f"{Colors.YELLOW}[!]{Colors.END} {msg}")


def print_error(msg: str):
    """
    Affiche un message d'erreur avec le préfixe [ERREUR] en rouge.
    
    Résultat : [ERREUR] Description de l'erreur
    
    Paramètres:
        msg (str): Le message d'erreur à afficher
    """
    print(f"{Colors.RED}[ERREUR]{Colors.END} {msg}")


def print_progress(current: int, total: int, prefix: str = ""):
    """
    Affiche une barre de progression.
    
    Résultat : [████████░░░░░░░░░░░░] 40% - Traitement...
    
    Paramètres:
        current (int): Valeur actuelle
        total (int): Valeur totale
        prefix (str): Texte à afficher avant la barre
    """
    percent = (current / total) * 100
    bar_length = 20
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    end_char = '\n' if current >= total else '\r'
    print(f"{prefix}[{bar}] {percent:.0f}%", end=end_char)


def print_box(content: str, color: str = Colors.CYAN, emoji: str = ""):
    """
    Affiche un contenu dans une boîte formatée.
    
    Paramètres:
        content (str): Contenu à afficher
        color (str): Couleur de la boîte
        emoji (str): Emoji à afficher (optionnel)
    """
    padding = 3
    content_width = len(content) + 2 * padding
    
    if emoji:
        display = f"{emoji}  {content}  {emoji}"
    else:
        display = f"  {content}  "
    
    box_width = len(display) + 4
    
    print()
    print(f"    {color}{Colors.BOLD}┌{'─' * box_width}┐{Colors.END}")
    print(f"    {color}{Colors.BOLD}│{' ' * box_width}│{Colors.END}")
    print(f"    {color}{Colors.BOLD}│  {display}  │{Colors.END}")
    print(f"    {color}{Colors.BOLD}│{' ' * box_width}│{Colors.END}")
    print(f"    {color}{Colors.BOLD}└{'─' * box_width}┘{Colors.END}")
    print()
