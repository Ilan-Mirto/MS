const boutons_creer_party = document.querySelectorAll(".create-party-button");

for (const bouton_creer_party of boutons_creer_party) {
    if (bouton_creer_party.dataset.sessionIsHosting.toLowerCase() === "true") {
        bouton_creer_party.removeAttribute("href");
        bouton_creer_party.setAttribute("aria-disabled", "true");
        bouton_creer_party.tabIndex = -1;
    }
}
