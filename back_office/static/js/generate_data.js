document.getElementById("generateDataForm").addEventListener("submit", async function(event) {
    // Validation de la date de début
    const startDateInput = document.getElementById("start_date");
    const startDate = new Date(startDateInput.value);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (startDate >= today) {
        event.preventDefault(); // Empêche la soumission du formulaire
        alert("La date de début doit être antérieure à la date du jour.");
        return;
    }

    event.preventDefault();
    document.getElementById('loading').style.display = 'block';
    const submitButton = document.getElementById('submitButton');
    submitButton.classList.add('disabled');
    submitButton.disabled = true;

    // Soumettre le formulaire via AJAX
    const formData = new FormData(event.target);
    const response = await fetch(event.target.action, {
        method: 'POST',
        body: formData
    });

    const result = await response.json();

    // Vérifier régulièrement l'état de la tâche
    const checkTaskStatus = async () => {
        const statusResponse = await fetch(`/back-office/generate-data-status/${result.task_id}`);
        const statusResult = await statusResponse.json();

        if (statusResult.status === 'completed') {
            // La tâche est terminée, redirigez vers la page suivante
            window.location.href = '/back-office/login';
        } else if (statusResult.status === 'running') {
            // La tâche est en cours, vérifiez à nouveau dans quelques secondes
            setTimeout(checkTaskStatus, 5000); // 5000 ms = 5 secondes
        } else {
            // Gérer les autres statuts ou les erreurs ici
        }
    };

    // Lancer la vérification de l'état de la tâche
    checkTaskStatus();
});
