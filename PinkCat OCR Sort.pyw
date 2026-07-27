"""
OrganizadorFotos - Punto de entrada principal
Ejecutar este archivo para lanzar la aplicación (sin consola).
"""
import sys
import os

# Asegurar que los módulos locales sean encontrados
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import OrganizadorApp

if __name__ == "__main__":
    app = OrganizadorApp()
    app.mainloop()
