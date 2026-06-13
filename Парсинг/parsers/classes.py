def get_class_links():

    response = session.get(f"{BASE_URL}/class/")
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    links = []

    for a in soup.find_all("a"):

        href = a.get("href")

        if href and href.startswith("/class/"):

            links.append(BASE_URL + href)

    return list(set(links))