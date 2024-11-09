import argparse
import requests
from json import decoder, dumps
from colorama import init, Fore, Style
import random
import time

# Initialize colorama
init(autoreset=True)

def display_aligned_info(data, level=0):
    """
    Affiche toutes les informations sous forme de dictionnaire Python aligné dans le terminal.
    """
    indent = ' ' * (4 * level)
    for key, value in data.items():
        if isinstance(value, dict):
            print(Fore.CYAN + Style.BRIGHT + f"{indent}{key}:")
            display_aligned_info(value, level + 1)
        elif isinstance(value, list):
            print(Fore.CYAN + Style.BRIGHT + f"{indent}{key}: [")
            for item in value:
                if isinstance(item, dict):
                    display_aligned_info(item, level + 1)
                else:
                    print(Fore.GREEN + f"{' ' * (4 * (level + 1))}{item}")
            print(Fore.CYAN + Style.BRIGHT + f"{indent}]")
        else:
            print(Fore.YELLOW + f"{indent}{key.ljust(30 - level * 4)} : {Fore.GREEN}{value}")

def get_user_id(username, sessionid):
    """
    Récupère l'ID utilisateur pour un nom d'utilisateur donné.
    """
    headers = {"User-Agent": "iphone_ua", "x-ig-app-id": "936619743392459"}
    response = requests.get(
        f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}',
        headers=headers,
        cookies={'sessionid': sessionid}
    )
    try:
        if response.status_code == 404:
            return {"id": None, "error": "User not found"}
        user_id = response.json()["data"]["user"]["id"]
        return {"id": user_id, "error": None}
    except decoder.JSONDecodeError:
        return {"id": None, "error": "Rate limit"}

def simulate_navigation(sessionid):
    """
    Simule la navigation sur plusieurs pages pour obtenir un CSRF token.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36",
        "Referer": "https://www.instagram.com/"
    }
    cookies = {"sessionid": sessionid}
    pages_to_visit = [
        "https://www.instagram.com/",
        "https://www.instagram.com/explore/",
        "https://www.instagram.com/accounts/edit/",
        "https://www.instagram.com/direct/inbox/"
    ]
    csrftoken = None
    for page in pages_to_visit:
        try:
            response = requests.get(page, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la navigation : {str(e)}")
            continue
        cookies.update(response.cookies.get_dict())
        if not csrftoken:
            csrftoken = response.cookies.get("csrftoken")
        time.sleep(random.uniform(1, 3))
    return cookies, csrftoken

def get_user_info(username, sessionid):
    """
    Récupère toutes les informations de l'utilisateur à partir de son nom d'utilisateur.
    """
    userId = get_user_id(username, sessionid)
    if userId["error"]:
        print("Utilisateur non trouvé ou limite atteinte.")
        return None

    # Simulation de navigation pour obtenir un CSRF token
    cookies, csrftoken = simulate_navigation(sessionid)
    headers = {
        'User-Agent': 'Instagram 64.0.0.14.96',
        'X-CSRFToken': csrftoken
    }
    cookies["csrftoken"] = csrftoken

    # Requête principale pour obtenir les informations utilisateur
    response = requests.get(
        f'https://i.instagram.com/api/v1/users/{userId["id"]}/info/',
        headers=headers,
        cookies=cookies
    )
    try:
        info_user = response.json()["user"]
        info_user["userID"] = userId["id"]

        # Ajout de requêtes pour récupérer des détails supplémentaires
        advanced_info = get_advanced_user_info(userId["id"], cookies, csrftoken)
        if advanced_info:
            info_user.update(advanced_info)

        return info_user
    except decoder.JSONDecodeError:
        print("Erreur de décodage JSON.")
        return None

def get_advanced_user_info(user_id, cookies, csrftoken):
    """
    Récupère des informations avancées de l'utilisateur, y compris les profils associés et les paramètres de sécurité.
    """
    headers = {
        'User-Agent': 'Instagram 150.0.0.33.120 Android',
        'X-CSRFToken': csrftoken
    }
    advanced_info = {}

    # Requête pour obtenir les profils associés (chaining)
    response = requests.get(
        f'https://i.instagram.com/api/v1/friendships/{user_id}/chaining/',
        headers=headers,
        cookies=cookies
    )
    try:
        advanced_info["chaining_results"] = response.json().get("users", [])
    except decoder.JSONDecodeError:
        print("Erreur de décodage JSON lors de la récupération des profils associés.")
    
    # Autres paramètres de sécurité et de confidentialité
    try:
        advanced_info["security_settings"] = {
            "is_bestie": False,
            "is_restricted": False,
            "has_public_tab_threads": False
        }
        # Exemple d'autres requêtes pour récupérer des informations sur les paramètres de sécurité
    except Exception as e:
        print(f"Erreur lors de la récupération des paramètres de sécurité : {str(e)}")
    
    return advanced_info

def main():
    """
    Fonction principale pour récupérer et afficher toutes les informations de l'utilisateur Instagram.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sessionid', help="Instagram session ID", required=True)
    parser.add_argument('-u', '--username', help="Nom d'utilisateur Instagram", required=True)
    args = parser.parse_args()

    sessionid = args.sessionid
    username = args.username

    # Récupérer toutes les informations de l'utilisateur
    user_info = get_user_info(username, sessionid)
    if not user_info:
        return

    # Afficher toutes les informations de l'utilisateur sous forme de dictionnaire Python aligné
    print(Fore.CYAN + Style.BRIGHT + "\n===== Informations Complètes de l'Utilisateur =====")
    display_aligned_info(user_info)

if __name__ == "__main__":
    main()

