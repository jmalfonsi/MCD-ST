# Prototype mapping POC

Prototype jetable pour valider le principe du mapping automatisé MCD-ST sans interface graphique.

Question testée :

> Des exports hétérogènes de logiciel SPSTi peuvent-ils être profilés, reliés, mappés intelligemment vers quelques tables MCD-ST, puis transformés en dry-run avec une revue humaine simulée ?

Lancer :

```bash
python3 prototypes/mapping_poc/mapping_poc.py
```

Le script génère des exports synthétiques, propose un mapping scoré, produit un fichier YAML et crée des tables MCD-ST de démonstration dans :

```text
prototypes/mapping_poc/_scratch_PROTOTYPE_WIPE_ME/
```

Ce dossier est volontairement jetable.

Le verdict produit a été absorbé dans la spécification durable du moteur de mapping : [../../docs/MAPPING_ENGINE_SPEC.md](../../docs/MAPPING_ENGINE_SPEC.md).
