from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from validate_email import validate_email
from flask import Flask, Response
from flask import request, flash, redirect, render_template, url_for
import sys, re, dns.resolver, random, string


email_finder = Flask(__name__, static_folder='templates', template_folder='templates')
email_finder.secret_key = ''.join(random.choice(string.ascii_letters + string.digits)for i in range(24))


@email_finder.route('/')
def index():
    return render_template('index.html')
###################################################################################################
# PAGE D'ACCUEIL

@email_finder.route('/', methods=['GET','POST'])
def home():
    error_message = None
    global domain_search
    domain_search = ' '
    if request.method == 'POST':
        domain_search = request.form.get('domain_search')
        return redirect(url_for('result'))
    return render_template('index.html', error_message=error_message)
    
###################################################################################################
# VALIDATION DU DOMAINE 

# def validation_domaine():
#     # domain_search = request.args.get('domain_search')
#     global domain_search
#     if request.method == 'GET':
#         if validate_email(f"test@{domain_search}", check_mx=True)==False:
#             # print(validate_email(f"test@{domain_search}", check_mx=True),"@@@@@@@@@@@@@@@@@@@@@@")
#             error_message_domain = f"Le domaine {domain_search} n'est pas valide."
#             # print(validate_email(f"test@{nom_domaine}", check_mx=True),"####################")
#             return redirect(url_for('home', error_message=error_message_domain))
#         else:
#             return redirect(url_for('result'))

###################################################################################################
# RECHERCHE DU DOMAINE DANS LA BDD

email_trouve_bdd = []
def verification_bdd():
    global domain_search
    global email_trouve_bdd
    with open('bdd.txt', "r") as bdd_email:
        contenu_bdd = bdd_email.read().rstrip('\n')
        index = contenu_bdd.find(domain_search)
        if index != -1:
            # Si le domaine est présent dans la bdd, on récupère les occurences
            start_index = max(0, index-20)
            end_index = contenu_bdd.find(' ', index)
            if end_index == -1:
                email_trouve_bdd.append(contenu_bdd[start_index:])
            else:
                email_trouve_bdd.append(contenu_bdd[start_index:end_index])
    email_trouve_bdd = email_trouve_bdd[0].split('\n')
    print(email_trouve_bdd,'1#1#1#1#1#1#1#1#11##1#1#1#1#')
    return email_trouve_bdd
    


###################################################################################################
# AJOUT DANS LA BDD
def ajout_bdd():
    with open('bdd.txt', 'r') as f:
        bdd_emails = f.read().splitlines()

    for email_trouve in email_trouves:
        if email_trouve not in bdd_emails:
            with open('bdd.txt', 'a') as f:
                f.write(email_trouve + "\n")


    # Effacement du fichier contenant les html
    with open("google_results.txt", "w") as html_recherche:
        html_recherche.write("")


###################################################################################################
# RESULTAT DE LA RECHERCHE

@email_finder.route('/result/', methods=['GET', 'POST'])
def result():
    global email_trouves
    global email_trouve_bdd
    # domain_search = request.args.get('domain_search')

    # validation_domaine()
    verification_bdd()
    # print(domain_search, type(domain_search),'##################')

    # Ensuite on lance le scraping

    # Créer des options pour le navigateur Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')

    # Ouvrir le navigateur Google Chrome
    service = Service(executable_path='/Users/rylesbengougam/Desktop/email/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)


    # Naviguer vers la page de recherche de Google
    driver.get("https://www.google.com")

    #Refuser les cookies
    try:
        cookie = driver.find_element(By.XPATH, value='//*[@id="W0wltc"]/div')
        WebDriverWait(driver, 10).until(EC.visibility_of(cookie))
        cookie.click()
    except:
        pass

    # Trouver la barre de recherche et saisir les mots-clés
    #search_box = driver.find_element_by_name("q")
    search_box = driver.find_element(By.NAME, 'q')
    search_box.send_keys('"@'+domain_search+'"')
    search_box.send_keys(Keys.RETURN)


    # Attendre que la page de résultats se charge
    driver.implicitly_wait(10)


    # Extraire le code HTML de chaque résultat de recherche
    email_trouves = driver.find_elements(By.CLASS_NAME,value='MjjYud')
    html_codes = []
    for email_trouve in email_trouves:
        html_codes.append(email_trouve.get_attribute('innerHTML'))

    try:
        # Recherche de l'élément avec le nom de classe "d6cvqb BBwThe"
        page_suivante = driver.find_element(By.XPATH,value='//*[@id="pnnext"]')

        # Vérification si l'élément contient un URL
        try:
            url = page_suivante.get_attribute("href")
            if url:
                # Si l'élément contient un URL, clic sur l'URL
                page_suivante.click()
                # Extraire le code HTML de chaque résultat de recherche
                email_trouves = driver.find_elements(By.CLASS_NAME,value='MjjYud')
                for email_trouve in email_trouves:
                    html_codes.append(email_trouve.get_attribute('innerHTML'))
        except:
            pass
    except:
            pass

    contenu = ' '.join(html_codes)

    # Fermer le navigateur
    driver.quit()

    # Conversion de la variable HTML en objet BeautifulSoup
    soup = BeautifulSoup(contenu, 'html.parser')

    # Conversion du contenu HTML en texte
    contenu_texte = soup.get_text()

    # Suppression de la chaîne "<em>"
    contenu_texte_modifie = contenu_texte.replace('<em>', '')

    # Affichage du contenu texte modifié
    #print(contenu_texte_modifie)

    # Rechercher toutes les occurrences du mot-clé
    occurrences = contenu_texte_modifie.count("@" + domain_search)

    # Ajouter les lettres directement à gauche de chaque occurrence
    email_trouves = []
    start_index = 0
    while True:
        # Chercher la prochaine occurrence à partir de l'index de départ
        index = contenu_texte_modifie.find("@"+domain_search, start_index)
        if index == -1:
            # Toutes les occurrences ont été trouvées
            break
        
        # Trouver le premier espace à gauche de l'occurrence
        space_index = contenu_texte_modifie.rfind(' ' or '..', 0, index)
        if space_index == -1:
            # Pas d'espace trouvé, utiliser le début de la chaîne
            start = contenu_texte_modifie[:index]
        else:
            # Utiliser les lettres entre l'espace et l'occurrence
            start = contenu_texte_modifie[space_index+1:index]
        
        # Ajouter le résultat à la liste
        email_trouves.append(start + "@"+ domain_search)

        # Ajouter le résultat à la bdd
        ajout_bdd()
    
        # Définir le nouvel index de départ pour la recherche suivante
        start_index = index + 1
        print(email_trouves,'#############################')
        print(email_trouve_bdd,'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
        email_resultat_couples = list(set(email_trouves + email_trouve_bdd))
    return render_template('result.html', email_resultat_couples=email_resultat_couples, nb_sites = len(html_codes))


###################################################################################################    

if __name__ == '__main__':
    email_finder.run(debug=True)


