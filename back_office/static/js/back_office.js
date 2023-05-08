function validateInput(input) {
    // Suppressions de tous les caractères non numériques sauf les espaces
    input.value = input.value.replace(/[^\d\s]/g, '');
  
    // Suppressions des espaces
    let num = input.value.replace(/\s/g, '');
  
    // Ajout d'un espace entre les groupes de 3 chiffres
    input.value = num.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }