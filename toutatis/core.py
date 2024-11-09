import argparse
import requests
from urllib.parse import quote_plus
from json import decoder, dumps
from colorama import init, Fore, Style
import random
import time

# Initialize colorama
init(autoreset=True)

def getUserId(username, sessionid):
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

def getInfo(username, sessionid):
    userId = getUserId(username, sessionid)
    if userId["error"]:
        return userId

    response = requests.get(
        f'https://i.instagram.com/api/v1/users/{userId["id"]}/info/',
        headers={'User-Agent': 'Instagram 64.0.0.14.96'},
        cookies={'sessionid': sessionid}
    )
    try:
        infoUser = response.json()["user"]
        infoUser["userID"] = userId["id"]
        
        # Afficher le JSON complet
        print(Fore.MAGENTA + Style.BRIGHT + "\nDonnées JSON complètes :")
        print_recursive(infoUser)
        
        return {"user": infoUser, "error": None}
    except decoder.JSONDecodeError:
        print(Fore.RED + Style.BRIGHT + "Erreur de décodage JSON.")
        print(Fore.WHITE + Style.BRIGHT + response.text)
        return {"user": None, "error": "Erreur de décodage JSON"}

def print_recursive(data, level=0):
    """
    Fonction récursive pour afficher toutes les informations dans le JSON.
    """
    indent = ' ' * (4 * level)
    if isinstance(data, dict):
        for key, value in data.items():
            print(Fore.YELLOW + f"{indent}{key}: ", end="")
            if isinstance(value, (dict, list)):
                print()
                print_recursive(value, level + 1)
            else:
                print(Fore.GREEN + f"{value}")
    elif isinstance(data, list):
        for item in data:
            print_recursive(item, level + 1)

def advanced_lookup(username, sessionid, recovery_method):
    """
    Post request to get obfuscated login information (similar to how Toutatis does).
    """
    cookies, csrftoken = simulate_navigation(sessionid)
    if not csrftoken:
        return "Erreur : CSRF token introuvable après la navigation."
    # Rotation des User-Agents
    user_agents = [
        "Instagram 150.0.0.33.120 Android (29/10; 320dpi; 720x1280; Samsung; SM-G973F; beyond1; exynos9820; en_US; 230767795)",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Instagram 123.0.0.21.114 Android (30/10; 420dpi; 1080x1920; OnePlus; ONEPLUS A5010; OnePlus5T; qcom; en_US; 200322364)"
    ]
    headers = {
        "User-Agent": random.choice(user_agents),
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-IG-App-ID": "124024574287414",
        "Accept-Encoding": "gzip, deflate",
        "Host": "i.instagram.com",
        "Connection": "keep-alive",
        "X-CSRFToken": csrftoken
    }
    cookies["csrftoken"] = csrftoken
    data = "signed_body=SIGNATURE." + quote_plus(dumps(
        {"q": username, "skip_recovery": "1", "recovery_method": recovery_method},
        separators=(",", ":")
    ))
    try:
        response = requests.post(
            "https://i.instagram.com/api/v1/users/lookup/",
            headers=headers,
            cookies=cookies,
            data=data,
            timeout=10
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Erreur lors de la requête : {str(e)}"
    if response.status_code == 200:
        try:
            response_data = response.json()
            hint = ""
            if "obfuscated_email" in response_data:
                hint += f"Obfuscated Email: {response_data['obfuscated_email']}\n"
            if "obfuscated_phone" in response_data:
                hint += f"Obfuscated Phone: {response_data['obfuscated_phone']}\n"
            return hint if hint else "Aucune information de récupération trouvée."
        except ValueError:
            return "Erreur de décodage JSON."
    elif response.status_code == 400 and "useragent mismatch" in response.text:
        return "Erreur : Le User-Agent ne correspond pas. Essayez un autre User-Agent."
    else:
        return f"Erreur lors de la requête : {response.status_code}"

def simulate_navigation(sessionid):
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
        time.sleep(random.uniform(1, 3))  # Pause aléatoire entre les requêtes pour simuler une navigation humaine
    return cookies, csrftoken

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sessionid', help="Instagram session ID", required=True)
    parser.add_argument('-u', '--username', help="Nom d'utilisateur Instagram", required=True)
    parser.add_argument('-r', '--recovery_method', help="Méthode de récupération (email, sms, wa)", default="email")
    args = parser.parse_args()

    sessionid = args.sessionid
    username = args.username

    infos = getInfo(username, sessionid)
    if not infos["user"]:
        exit(infos["error"])

    # Affichage des informations JSON complètes de l'utilisateur
    print("\n===== Informations complètes de l'utilisateur =====")
    print_recursive(infos["user"])

    # Récupération des informations de récupération (obfuscated)
    other_infos = advanced_lookup(username, sessionid, args.recovery_method)
    print(Fore.CYAN + Style.BRIGHT + "\nInformations de récupération (obfusquées) :")
    print(other_infos)

if __name__ == "__main__":
    main()

