"""Services métier du catalogue et chargement contrôlé des références."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from apps.activities.models import Activity

from .models import CatalogCategory, Product, Service


REFERENCE_SOURCE = (
    "Référentiels workflow/catalogue_prix_cameroun_2026.pdf et "
    "workflow/catalogue_prix_references_commerces_cameroun_novembre_2026.pdf, "
    "relevé du 08/11/2026"
)

REFERENCE_CATALOG = {
    "restaurant-bar": {
        "categories": [
            ("Bières", "bieres"),
            ("Boissons sans alcool", "boissons-sans-alcool"),
            ("Jus", "jus"),
            ("Eaux", "eaux"),
            ("Spiritueux", "spiritueux"),
            ("Vins et mousseux", "vins-mousseux"),
            ("Plats", "plats"),
        ],
        "products": [
            ("bieres", "Mutzig 50 cl", "mutzig-50cl", "canette de 50 cl", "700", "Prix unitaire relevé en ligne."),
            ("bieres", "Beaufort Lager 50 cl", "beaufort-50cl", "canette de 50 cl", "700", "Prix unitaire relevé en ligne."),
            ("bieres", "33 Export 50 cl", "33-export-50cl", "canette de 50 cl", "725", "Prix unitaire relevé à Douala."),
            ("bieres", "Castel Beer 50 cl", "castel-beer-50cl", "canette de 50 cl", "725", "Prix unitaire relevé en ligne."),
            ("bieres", "Hollandia 50 cl", "hollandia-50cl", "bouteille de 50 cl", "750", "Prix unitaire relevé en ligne."),
            ("bieres", "San Miguel Clara 33 cl", "san-miguel-clara-33cl", "bouteille de 33 cl", "800", "Prix unitaire relevé en ligne."),
            ("boissons-sans-alcool", "Top Ananas 35 cl", "top-ananas-35cl", "bouteille de 35 cl", "275", "Prix unitaire détaillant."),
            ("boissons-sans-alcool", "World Cola 35 cl", "world-cola-35cl", "bouteille de 35 cl", "275", "Prix unitaire détaillant."),
            ("boissons-sans-alcool", "Top Orange 1 L", "top-orange-1l", "bouteille de 1 L", "500", "Prix unitaire détaillant."),
            ("boissons-sans-alcool", "Vimto fruits rouges 33 cl", "vimto-33cl", "canette de 33 cl", "500", "Prix unitaire détaillant."),
            ("jus", "Frutas raisin ou cocktail 1 L", "frutas-jus-1l", "bouteille de 1 L", "950", "Prix unitaire affiché."),
            ("jus", "Aone jus de mangue 25 cl", "aone-mangue-25cl", "bouteille de 25 cl", "500", "Prix unitaire affiché."),
            ("eaux", "Tangui 1,5 L", "tangui-15l", "bouteille de 1,5 L", "275", "Prix unitaire affiché."),
            ("eaux", "Vitale 1,5 L", "vitale-15l", "bouteille de 1,5 L", "200", "Prix unitaire affiché."),
            ("spiritueux", "Vegas Whisky 1 L", "vegas-whisky-1l", "bouteille de 1 L", "5200", "Prix affiché en ligne."),
            ("spiritueux", "Magoustan's Original 1 L", "magoustans-rhum-1l", "bouteille de 1 L", "6700", "Prix affiché en ligne."),
            ("vins-mousseux", "J.P. Chenet Merlot 75 cl", "jp-chenet-merlot-75cl", "bouteille de 75 cl", "4000", "Prix affiché en ligne."),
            ("vins-mousseux", "Muscador", "muscador-75cl", "bouteille de 75 cl", "5700", "Prix affiché en ligne."),
            ("plats", "Poulet grillé", "poulet-grille-portion", "portion", "3000", "Prix de plat publié à Yaoundé."),
        ],
        "services": [],
    },
    "coiffure": {
        "categories": [
            ("Coiffure homme et enfant", "coiffure-homme-enfant"),
            ("Coiffure femme", "coiffure-femme"),
            ("Soins capillaires", "soins-capillaires"),
            ("Maquillage", "maquillage"),
        ],
        "products": [
            ("soins-capillaires", "Huile de croissance capillaire 100 ml", "huile-croissance-100ml", "flacon de 100 ml", "6000", "Prix affiché en ligne, gamme boutique."),
            ("soins-capillaires", "Shampooing afro Prescy 250 ml", "shampooing-prescy-250ml", "flacon de 250 ml", "4400", "Prix affiché en ligne."),
            ("soins-capillaires", "Après-shampooing profond 250 ml", "apres-shampooing-profond-250ml", "flacon de 250 ml", "6000", "Prix affiché en ligne."),
            ("soins-capillaires", "Après-shampooing sans rinçage 250 ml", "apres-shampooing-sans-rincage-250ml", "flacon de 250 ml", "5200", "Prix affiché en ligne."),
            ("soins-capillaires", "Beurre hydratant 250 ml", "beurre-hydratant-250ml", "pot de 250 ml", "4800", "Prix affiché en ligne."),
            ("soins-capillaires", "Brume capillaire aux plantes 250 ml", "brume-capillaire-250ml", "flacon de 250 ml", "4400", "Prix affiché en ligne."),
            ("maquillage", "Faux cils en bande", "faux-cils-bande", "unité", "5000", "Prix affiché en ligne."),
            ("maquillage", "Mascara noir Vidrine Cosmetics", "mascara-vidrine", "unité", "5000", "Prix affiché en ligne."),
        ],
        "services": [
            ("coiffure-homme-enfant", "Coiffure enfant", "coiffure-enfant", "1000", 30, "Prix relevé à Douala."),
            ("coiffure-homme-enfant", "Coiffure homme simple / dégradé", "coiffure-homme-simple", "2000", 45, "Prix relevé à Douala."),
            ("coiffure-homme-enfant", "Coupe simple homme", "coupe-simple-homme", "1000", 30, "Fourchette de référence : 1 000 à 3 000 FCFA; prix chargé au minimum indicatif."),
            ("coiffure-homme-enfant", "Coupe + barbe / finition", "coupe-barbe", "2500", 45, "Fourchette de référence : 2 500 à 5 000 FCFA; prix chargé au minimum indicatif."),
            ("coiffure-femme", "Tresses simples sans mèches", "tresses-simples", "1500", 120, "Fourchette de référence : 1 500 à 10 000 FCFA; prix chargé au minimum indicatif."),
            ("coiffure-femme", "Tresses avec mèches / braids", "tresses-avec-meches", "3000", 180, "Fourchette de référence : 3 000 à 25 000 FCFA; prix chargé au minimum indicatif."),
            ("coiffure-femme", "Pose de tissage", "pose-tissage", "2500", 120, "Fourchette de référence : 2 500 à 20 000 FCFA; prix chargé au minimum indicatif."),
            ("coiffure-femme", "Pose perruque / closure", "pose-perruque-closure", "5000", 90, "Fourchette de référence : 5 000 à 40 000 FCFA; prix chargé au minimum indicatif."),
            ("coiffure-femme", "Défrisage + mise en plis", "defrisage-mise-en-plis", "2000", 90, "Fourchette de référence : 2 000 à 12 000 FCFA; prix chargé au minimum indicatif."),
            ("coiffure-femme", "Chignon / cérémonie", "chignon-ceremonie", "2000", 90, "Fourchette de référence : 2 000 à 20 000 FCFA; prix chargé au minimum indicatif."),
            ("coiffure-femme", "Manucure spa", "manucure-spa", "5000", 60, "Prix affiché par Ella Beauty."),
            ("coiffure-femme", "Pose vernis gel", "vernis-gel", "5000", 60, "Prix affiché par Ella Beauty."),
            ("coiffure-femme", "Pédicure à sec", "pedicure-sec", "5000", 60, "Prix affiché par Ella Beauty."),
        ],
    },
    "boutique": {
        "categories": [
            ("Épicerie et alimentation", "epicerie-alimentation"),
            ("Entretien", "entretien"),
            ("Vêtements", "vetements"),
            ("Chaussures", "chaussures"),
            ("Cosmétiques", "cosmetiques"),
            ("Boissons", "boissons"),
        ],
        "products": [
            ("epicerie-alimentation", "Macaroni Broli 250 g", "macaroni-broli-250g", "paquet de 250 g", "240", "Prix détaillant."),
            ("epicerie-alimentation", "Macaroni Neima 250 g", "macaroni-neima-250g", "paquet de 250 g", "220", "Prix détaillant."),
            ("epicerie-alimentation", "Lait concentré sucré Peak 78 g", "lait-peak-78g", "boîte de 78 g", "450", "Prix détaillant."),
            ("epicerie-alimentation", "Riz parfumé Africana 5 kg", "riz-africana-5kg", "sac de 5 kg", "4800", "Prix détaillant."),
            ("epicerie-alimentation", "Thon Africana 200 g", "thon-africana-200g", "boîte de 200 g", "1100", "Promotion Carrefour, janvier 2026."),
            ("epicerie-alimentation", "Lait en poudre Nido 400 g", "lait-nido-400g", "boîte de 400 g", "3140", "Prix détaillant."),
            ("epicerie-alimentation", "Mayonnaise Aromate 450 g", "mayonnaise-aromate-450g", "pot de 450 g", "1990", "Promotion Carrefour, janvier 2026."),
            ("epicerie-alimentation", "Shortbread Cremica 85 g", "shortbread-cremica-85g", "paquet de 85 g", "400", "Promotion Carrefour, janvier 2026."),
            ("entretien", "Savon de toilette Azur", "savon-azur-carton", "carton de 60 × 400 g", "20500", "Prix grossiste; prix du carton, pas prix unitaire."),
            ("vetements", "T-shirt Stone°97", "t-shirt-stone97", "pièce", "10000", "Prix vendeur en ligne à Yaoundé."),
            ("vetements", "Polo Stone°97", "polo-stone97", "pièce", "8000", "Prix vendeur en ligne à Yaoundé."),
            ("vetements", "Chemise safari Elite / Prestige Polo", "chemise-safari", "pièce", "10350", "Prix marketplace Cameroun."),
            ("vetements", "Ensemble jogging Nike", "ensemble-jogging-nike", "ensemble", "22425", "Prix marketplace Cameroun; modèle listé."),
            ("chaussures", "Ballerines modèle jean", "ballerines-jean", "paire", "4900", "Prix boutique en ligne Cameroun."),
            ("chaussures", "Bottes modèle enfant", "bottes-enfant", "paire", "7500", "Prix boutique en ligne Cameroun."),
            ("cosmetiques", "Mascara noir Vidrine Cosmetics", "mascara-vidrine", "unité", "5000", "Prix affiché en ligne."),
            ("boissons", "Ovaltine 400 g", "ovaltine-400g", "boîte de 400 g", "2350", "Promotion Carrefour, janvier 2026."),
        ],
        "services": [],
    },
}


def load_reference_catalog(activity: Activity, *, dry_run: bool = False) -> dict[str, int]:
    """Crée les entrées absentes sans modifier les articles déjà présents."""
    reference = REFERENCE_CATALOG.get(activity.slug)
    if reference is None:
        raise ValueError(f"Aucun catalogue de référence prévu pour {activity.slug}.")

    result = {"categories_created": 0, "products_created": 0, "services_created": 0, "skipped": 0}
    categories: dict[str, CatalogCategory] = {}

    with transaction.atomic():
        for name, token in reference["categories"]:
            slug = f"ref-{token}"
            category = CatalogCategory.objects.filter(activity=activity, slug=slug).first()
            if category is None:
                category = CatalogCategory(
                    activity=activity,
                    name=name,
                    slug=slug,
                    sort_order=len(categories),
                    is_active=True,
                )
                if not dry_run:
                    category.save()
                result["categories_created"] += 1
            else:
                result["skipped"] += 1
            categories[token] = category

        for token, name, item_slug, unit, price, note in reference["products"]:
            if Product.objects.filter(activity=activity, slug=f"ref-{item_slug}").exists():
                result["skipped"] += 1
                continue
            if not dry_run:
                Product.objects.create(
                    activity=activity,
                    category=categories[token],
                    name=name,
                    slug=f"ref-{item_slug}",
                    unit=unit,
                    description=f"{note} {REFERENCE_SOURCE}. Prix indicatif à valider localement.",
                    price=Decimal(price),
                    is_active=True,
                    stock_quantity=0,
                    average_cost=Decimal("0"),
                )
            result["products_created"] += 1

        for token, name, item_slug, price, duration, note in reference["services"]:
            if Service.objects.filter(activity=activity, slug=f"ref-{item_slug}").exists():
                result["skipped"] += 1
                continue
            if not dry_run:
                Service.objects.create(
                    activity=activity,
                    category=categories[token],
                    name=name,
                    slug=f"ref-{item_slug}",
                    description=f"{note} {REFERENCE_SOURCE}. Prix indicatif à valider localement.",
                    price=Decimal(price),
                    duration_minutes=duration,
                    is_active=True,
                )
            result["services_created"] += 1

    return result
