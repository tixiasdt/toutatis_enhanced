import argparse
import requests
from urllib.parse import quote_plus
from json import decoder, dumps
from colorama import init, Fore, Style
import random
import time

# Initialisation de Colorama pour le formatage des couleurs dans la console
init(autoreset=True)

def get_user_id(username, sessionid):
    headers = {"User-Agent": "iphone_ua", "x-ig-app-id": "936619743392459"}
    response = requests.get(
        f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}',
        headers=headers,
        cookies={'sessionid': sessionid}
    )
    try:
        if response.status_code == 404:
            return {"id": None, "error": "Utilisateur non trouvé"}
        user_id = response.json()["data"]["user"]["id"]
        return {"id": user_id, "error": None}
    except decoder.JSONDecodeError:
        return {"id": None, "error": "Limite de requêtes atteinte"}

def get_info(username, sessionid):
    user_id_info = get_user_id(username, sessionid)
    if user_id_info["error"]:
        return user_id_info

    response = requests.get(
        f'https://i.instagram.com/api/v1/users/{user_id_info["id"]}/info/',
        headers={'User-Agent': 'Instagram 64.0.0.14.96'},
        cookies={'sessionid': sessionid}
    )
    try:
        user_info = response.json()["user"]
        user_info["userID"] = user_id_info["id"]
        
        print(Fore.CYAN + Style.BRIGHT + "\n===== Informations complètes de l'utilisateur =====" + Style.RESET_ALL)
        print_recursive(user_info)
        
        return {"user": user_info, "error": None}
    except decoder.JSONDecodeError:
        print(Fore.RED + Style.BRIGHT + "Erreur de décodage JSON.")
        print(Fore.WHITE + Style.BRIGHT + response.text)
        return {"user": None, "error": "Erreur de décodage JSON"}

def print_recursive(data, level=0):
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

def get_csrf_token(sessionid):
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36",
        "Referer": "https://www.instagram.com/"
    }
    cookies = {"sessionid": sessionid}
    response = requests.get("https://www.instagram.com/", headers=headers, cookies=cookies)
    if response.status_code == 200:
        return response.cookies.get("csrftoken", "CSRF token introuvable")
    else:
        return f"Erreur lors de la requête initiale : {response.status_code}"

def get_password_reset_hint(username, sessionid):
    csrftoken = get_csrf_token(sessionid)
    if "Erreur" in csrftoken or csrftoken == "CSRF token introuvable":
        return csrftoken

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-CSRFToken": csrftoken
    }
    cookies = {"sessionid": sessionid, "csrftoken": csrftoken}
    data = {
        "email_or_username": username,
        "queryParams": "{}"
    }
    response = requests.post(
        "https://www.instagram.com/accounts/account_recovery_send_ajax/",
        headers=headers,
        cookies=cookies,
        data=data
    )
    if response.status_code == 200:
        try:
            response_data = response.json()
            return response_data.get("contact_point", "Aucune information de récupération trouvée.")
        except ValueError:
            return "Erreur de décodage JSON."
    return f"Erreur lors de la requête : {response.status_code}"

def advanced_lookup(username, sessionid, recovery_method):
    cookies, csrftoken = simulate_navigation(sessionid)
    if not csrftoken:
        return {"obfuscated_email": None, "obfuscated_phone": None, "error": "CSRF token introuvable après la navigation."}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
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
        return {"obfuscated_email": f"Erreur lors de la requête : {str(e)}", "obfuscated_phone": None}

    if response.status_code == 200:
        try:
            response_data = response.json()
            obfuscated_email = response_data.get("obfuscated_email")
            obfuscated_phone = response_data.get("obfuscated_phone")
            # On ignore l'affichage si l'email obfusqué est simplement "*@gmail.com"
            if obfuscated_email == "*@gmail.com":
                obfuscated_email = None
            return {"obfuscated_email": obfuscated_email, "obfuscated_phone": obfuscated_phone}
        except ValueError:
            return {"obfuscated_email": "Erreur de décodage JSON.", "obfuscated_phone": None}

    return {"obfuscated_email": f"Erreur lors de la requête : {response.status_code}", "obfuscated_phone": None}

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
            cookies.update(response.cookies.get_dict())
            if not csrftoken:
                csrftoken = response.cookies.get("csrftoken")
            time.sleep(random.uniform(1, 3))
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la navigation : {str(e)}")
            continue
    return cookies, csrftoken

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sessionid', help="Instagram session ID", required=True)
    parser.add_argument('-u', '--username', help="Nom d'utilisateur Instagram", required=True)
    parser.add_argument('-r', '--recovery_method', help="Méthode de récupération (email, sms, wa)", default="email")
    args = parser.parse_args()

    sessionid = args.sessionid
    username = args.username

      

    # Récupération des informations utilisateur
    infos = get_info(username, sessionid)
    if infos.get("user"):
        print_recursive(infos["user"])
    else:
        print(Fore.RED + "Aucune information utilisateur trouvée.")

    # Toujours afficher le titre de la section

    # Ligne de séparation esthétique avant l'affichage des emails et téléphones obfusqués
    print(Fore.CYAN + Style.BRIGHT + "\n===== Informations complètes de l'utilisateur =====\n" + Style.RESET_ALL)


    # Récupération de l'email obfusqué
    email_hint = get_password_reset_hint(username, sessionid)
    if email_hint and email_hint != "*@gmail.com":
        print(Fore.CYAN + Style.BRIGHT + "Obfuscated Email: " + Style.RESET_ALL + email_hint)

    # Récupération du téléphone obfusqué avec Toutatis
    phone_hint = advanced_lookup(username, sessionid, args.recovery_method)
    if phone_hint["obfuscated_email"]:
        print(Fore.CYAN + Style.BRIGHT + "Obfuscated Email: " + Style.RESET_ALL + phone_hint["obfuscated_email"])
    if phone_hint["obfuscated_phone"]:
        print(Fore.CYAN + Style.BRIGHT + "Obfuscated Phone: " + Style.RESET_ALL + phone_hint["obfuscated_phone"])

    # Ligne de séparation finale pour un design plus propre
    print(Fore.CYAN + Style.BRIGHT + "\n--------------------------------------------------------\n" + Style.RESET_ALL)

if __name__ == "__main__":
    main()
