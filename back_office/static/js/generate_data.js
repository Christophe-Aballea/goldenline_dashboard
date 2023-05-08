document.getElementById("generateDataForm").addEventListener("submit", function(event) {
    const startDateInput = document.getElementById("start_date");
    const startDate = new Date(startDateInput.value);
    const today = new Date();
    
    // Assurez-vous que l'heure et les minutes sont réinitialisées pour effectuer une comparaison de date correcte
    today.setHours(0, 0, 0, 0);

    if (startDate >= today) {
        event.preventDefault(); // Empêche la soumission du formulaire
        alert("La date de début doit être antérieure à la date du jour.");
    }
});
