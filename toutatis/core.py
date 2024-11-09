import argparse
import requests
from urllib.parse import quote_plus
from json import dumps, decoder
import random
import time

import phonenumbers
from phonenumbers.phonenumberutil import region_code_for_country_code
import pycountry

def getUserId(username, sessionid):
    headers = {"User-Agent": "iphone_ua", "x-ig-app-id": "936619743392459"}
    api = requests.get(
        f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}',
        headers=headers,
        cookies={'sessionid': sessionid}
    )
    try:
        if api.status_code == 404:
            return {"id": None, "error": "User not found"}
        user_id = api.json()["data"]['user']['id']
        return {"id": user_id, "error": None}
    except decoder.JSONDecodeError:
        return {"id": None, "error": "Rate limit"}

def get_csrf_token(sessionid):
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36",
        "Referer": "https://www.instagram.com/"
    }
    cookies = {"sessionid": sessionid}
    try:
        response = requests.get("https://www.instagram.com/", headers=headers, cookies=cookies, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Erreur lors de la requête initiale : {str(e)}", None
    response_cookies = response.cookies
    csrftoken = response_cookies.get("csrftoken")
    if csrftoken:
        return csrftoken, response_cookies
    else:
        return "CSRF token introuvable", response_cookies

def simulate_navigation(sessionid):
    """
    Simuler la navigation sur plusieurs pages d'Instagram pour récupérer plus de cookies.
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
        time.sleep(random.uniform(1, 3))  # Pause aléatoire entre les requêtes pour simuler une navigation humaine
    return cookies, csrftoken

def getInfo(username, sessionid):
    userId = getUserId(username, sessionid)
    if userId["error"]:
        return userId

    response = requests.get(
        f'https://i.instagram.com/api/v1/users/{userId["id"]}/info/',
        headers={'User-Agent': 'Instagram 64.0.0.14.96'},
        cookies={'sessionid': sessionid}
    ).json()["user"]
    infoUser = response
    infoUser["userID"] = userId["id"]
    return {"user": infoUser, "error": None}

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sessionid', help="Instagram session ID", required=True)
    parser.add_argument('-u', '--username', help="One username", required=True)
    parser.add_argument('-r', '--recovery_method', help="Méthode de récupération (email, sms, wa)", default="email")
    args = parser.parse_args()

    sessionid = args.sessionid
    username = args.username

    infos = getInfo(username, sessionid)
    if not infos["user"]:
        exit(infos["error"])

    infos = infos["user"]
    print("Informations about     : " + infos["username"])
    print("userID                 : " + infos["userID"])
    print("Full Name              : " + infos["full_name"])
    print("Verified               : " + str(infos['is_verified']) + " | Is business Account : " + str(infos["is_business"]))
    print("Is private Account     : " + str(infos["is_private"]))
    print("Follower               : " + str(infos["follower_count"]) + " | Following : " + str(infos["following_count"]))
    print("Number of posts        : " + str(infos["media_count"]))
    if infos["external_url"]:
        print("External url           : " + infos["external_url"])
    print("IGTV posts             : " + str(infos["total_igtv_videos"]))
    print("Biography              : " + (f"""\n{" "*25}""").join(infos["biography"].split("\n")))
    print("Linked WhatsApp        : " + str(infos["is_whatsapp_linked"]))
    print("Memorial Account       : " + str(infos["is_memorialized"]))
    print("New Instagram user     : " + str(infos["is_new_to_instagram"]))
    if "public_email" in infos.keys():
        if infos["public_email"]:
            print("Public Email           : " + infos["public_email"])
    if "public_phone_number" in infos.keys():
        if str(infos["public_phone_number"]):
            phonenr = "+" + str(infos["public_phone_country_code"]) + " " + str(infos["public_phone_number"])
            try:
                pn = phonenumbers.parse(phonenr)
                countrycode = region_code_for_country_code(pn.country_code)
                country = pycountry.countries.get(alpha_2=countrycode)
                phonenr = phonenr + " ({}) ".format(country.name)
            except:
                pass
            print("Public Phone number    : " + phonenr)
    other_infos = advanced_lookup(username, sessionid, args.recovery_method)
    print(other_infos)

if __name__ == "__main__":
    main()
