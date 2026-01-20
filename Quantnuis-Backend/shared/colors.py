#!/usr/bin/env python3
"""
================================================================================
                    CODES COULEURS ANSI
================================================================================

Définition des codes ANSI pour l'affichage coloré dans le terminal.

Usage:
    from shared import Colors
    print(f"{Colors.GREEN}Succès !{Colors.END}")

================================================================================
"""


class Colors:
    """
    Codes ANSI pour colorer le texte dans le terminal.
    
    COMMENT ÇA MARCHE ?
    ───────────────────
    Les séquences d'échappement ANSI sont des caractères spéciaux interprétés
    par le terminal pour modifier l'affichage du texte.
    
    Structure : \\033[XXm
    - \\033 (ou \\x1b) : Caractère d'échappement (ESC)
    - [ : Début de la séquence
    - XX : Code de style/couleur
    - m : Fin de la séquence
    
    USAGE :
    ───────
    print(f"{Colors.GREEN}Texte vert{Colors.END}")
    print(f"{Colors.BOLD}{Colors.RED}Erreur en gras rouge{Colors.END}")
    
    IMPORTANT : Toujours terminer par Colors.END pour réinitialiser le style.
    """
    
    # --- COULEURS DE TEXTE ---
    CYAN = '\033[96m'      # Cyan clair   - Informations, titres
    GREEN = '\033[92m'     # Vert clair   - Succès, confirmations
    YELLOW = '\033[93m'    # Jaune clair  - Avertissements
    RED = '\033[91m'       # Rouge clair  - Erreurs
    BLUE = '\033[94m'      # Bleu clair   - Liens, références
    MAGENTA = '\033[95m'   # Magenta      - Mise en évidence spéciale
    WHITE = '\033[97m'     # Blanc        - Texte standard
    
    # --- STYLES DE TEXTE ---
    BOLD = '\033[1m'       # Gras         - Mise en évidence
    DIM = '\033[2m'        # Atténué      - Infos secondaires
    ITALIC = '\033[3m'     # Italique     - Notes
    UNDERLINE = '\033[4m'  # Souligné     - Liens
    
    # --- RÉINITIALISATION ---
    END = '\033[0m'        # Reset        - OBLIGATOIRE après chaque style
    
    # --- COULEURS DE FOND ---
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
