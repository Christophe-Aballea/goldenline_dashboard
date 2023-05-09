document.getElementById("generateDataForm").addEventListener("submit", function(event) {
    const startDateInput = document.getElementById("start_date");
    const startDate = new Date(startDateInput.value);
    const today = new Date();

    today.setHours(0, 0, 0, 0);

    if (startDate >= today) {
        event.preventDefault(); // Empêche la soumission du formulaire
        alert("La date de début doit être antérieure à la date du jour.");
    }
});


document.getElementById('generateDataForm').addEventListener('submit', function (event) {
    event.preventDefault();
    document.getElementById('loading').style.display = 'block';
    const submitButton = document.getElementById('submitButton');
    submitButton.classList.add('disabled');
    submitButton.disabled = true;
  
    // Soumettre le formulaire
    event.target.submit();
  });
  