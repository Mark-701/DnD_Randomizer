const API_URL = "http://localhost:3001";

let currentCharacter = null;

document.addEventListener("DOMContentLoaded", async () => {
    const statusText = document.getElementById("statusText");

    try {
        statusText.textContent = "Загрузка данных из PostgreSQL...";

        await loadRaces();
        await loadClasses();
        await loadBackgrounds();

        connectAbilityInputs();

        document
            .getElementById("generateButton")
            .addEventListener("click", generateCharacter);

        document
            .getElementById("downloadButton")
            .addEventListener("click", downloadCharacter);

        statusText.textContent = "Данные успешно загружены. Можно генерировать персонажа.";
    } catch (error) {
        console.error(error);

        statusText.textContent =
            "Ошибка загрузки данных: " + error.message;
    }
});

async function loadRaces() {
    const response = await fetch(API_URL + "/api/races");

    if (!response.ok) {
        throw new Error("Не удалось загрузить расы");
    }

    const races = await response.json();

    const raceSelect = document.getElementById("raceSelect");
    raceSelect.innerHTML = "";

    for (const race of races) {
        const option = document.createElement("option");
        option.value = race.id;
        option.textContent = race.name;
        raceSelect.appendChild(option);
    }
}

async function loadClasses() {
    const response = await fetch(API_URL + "/api/classes");

    if (!response.ok) {
        throw new Error("Не удалось загрузить классы");
    }

    const classes = await response.json();

    const classSelect = document.getElementById("classSelect");
    classSelect.innerHTML = "";

    for (const classItem of classes) {
        const option = document.createElement("option");
        option.value = classItem.id;
        option.textContent = classItem.name;
        classSelect.appendChild(option);
    }
}

async function loadBackgrounds() {
    const response = await fetch(API_URL + "/api/backgrounds");

    if (!response.ok) {
        throw new Error("Не удалось загрузить предыстории");
    }

    const backgrounds = await response.json();

    const backgroundSelect = document.getElementById("backgroundSelect");
    backgroundSelect.innerHTML = "";

    for (const background of backgrounds) {
        const option = document.createElement("option");
        option.value = background.id;
        option.textContent = background.name;
        backgroundSelect.appendChild(option);
    }
}

async function generateCharacter() {
    const statusText = document.getElementById("statusText");

    try {
        statusText.textContent = "Генерация персонажа...";

        let level = Number(document.getElementById("levelInput").value) || 1;

        if (level < 1) {
            level = 1;
        }

        if (level > 20) {
            level = 20;
        }

        document.getElementById("levelInput").value = level;

        const response = await fetch(API_URL + "/api/generate-character", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                level: level
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText);
        }

        currentCharacter = await response.json();

        fillCharacterForm(currentCharacter);

        document.getElementById("downloadButton").disabled = false;

        statusText.textContent = "Персонаж успешно сгенерирован.";
    } catch (error) {
        console.error(error);

        statusText.textContent =
            "Ошибка генерации персонажа: " + error.message;
    }
}

function fillCharacterForm(character) {
    document.getElementById("raceSelect").value = String(character.raceId);
    document.getElementById("classSelect").value = String(character.classId);
    document.getElementById("backgroundSelect").value = String(character.backgroundId);
    document.getElementById("levelInput").value = character.level;

    document.getElementById("strengthInput").value = character.abilities["Сила"];
    document.getElementById("dexterityInput").value = character.abilities["Ловкость"];
    document.getElementById("constitutionInput").value = character.abilities["Телосложение"];
    document.getElementById("intelligenceInput").value = character.abilities["Интеллект"];
    document.getElementById("wisdomInput").value = character.abilities["Мудрость"];
    document.getElementById("charismaInput").value = character.abilities["Харизма"];

    updateAllModifiers();

    document.getElementById("hpValue").textContent =
        character.currentHp + " / " + character.maxHp;

    document.getElementById("speedValue").textContent =
        character.speed;

    document.getElementById("hitDieValue").textContent =
        character.hitDie;

    document.getElementById("proficiencyValue").textContent =
        "+" + character.proficiencyBonus;
}

function connectAbilityInputs() {
    const inputs = [
        "strengthInput",
        "dexterityInput",
        "constitutionInput",
        "intelligenceInput",
        "wisdomInput",
        "charismaInput"
    ];

    for (const inputId of inputs) {
        document
            .getElementById(inputId)
            .addEventListener("input", updateCharacterFromInputs);
    }
}

function updateCharacterFromInputs() {
    updateAllModifiers();

    if (currentCharacter === null) {
        return;
    }

    currentCharacter.abilities["Сила"] =
        Number(document.getElementById("strengthInput").value) || 1;

    currentCharacter.abilities["Ловкость"] =
        Number(document.getElementById("dexterityInput").value) || 1;

    currentCharacter.abilities["Телосложение"] =
        Number(document.getElementById("constitutionInput").value) || 1;

    currentCharacter.abilities["Интеллект"] =
        Number(document.getElementById("intelligenceInput").value) || 1;

    currentCharacter.abilities["Мудрость"] =
        Number(document.getElementById("wisdomInput").value) || 1;

    currentCharacter.abilities["Харизма"] =
        Number(document.getElementById("charismaInput").value) || 1;

    currentCharacter.modifiers["Сила"] =
        getAbilityModifier(currentCharacter.abilities["Сила"]);

    currentCharacter.modifiers["Ловкость"] =
        getAbilityModifier(currentCharacter.abilities["Ловкость"]);

    currentCharacter.modifiers["Телосложение"] =
        getAbilityModifier(currentCharacter.abilities["Телосложение"]);

    currentCharacter.modifiers["Интеллект"] =
        getAbilityModifier(currentCharacter.abilities["Интеллект"]);

    currentCharacter.modifiers["Мудрость"] =
        getAbilityModifier(currentCharacter.abilities["Мудрость"]);

    currentCharacter.modifiers["Харизма"] =
        getAbilityModifier(currentCharacter.abilities["Харизма"]);

    recalculateHp();
}

function updateAllModifiers() {
    updateModifier("strengthInput", "strengthModifier");
    updateModifier("dexterityInput", "dexterityModifier");
    updateModifier("constitutionInput", "constitutionModifier");
    updateModifier("intelligenceInput", "intelligenceModifier");
    updateModifier("wisdomInput", "wisdomModifier");
    updateModifier("charismaInput", "charismaModifier");
}

function updateModifier(inputId, modifierId) {
    const score = Number(document.getElementById(inputId).value) || 1;
    const modifier = getAbilityModifier(score);

    document.getElementById(modifierId).textContent =
        formatModifier(modifier);
}

function getAbilityModifier(score) {
    return Math.floor((score - 10) / 2);
}

function formatModifier(modifier) {
    if (modifier >= 0) {
        return "+" + modifier;
    }

    return String(modifier);
}

function recalculateHp() {
    if (currentCharacter === null) {
        return;
    }

    const constitutionModifier =
        getAbilityModifier(currentCharacter.abilities["Телосложение"]);

    const level = Number(document.getElementById("levelInput").value) || 1;

    const newHp = calculateHp(
        currentCharacter.hitDie,
        level,
        constitutionModifier
    );

    currentCharacter.maxHp = newHp;
    currentCharacter.currentHp = newHp;

    document.getElementById("hpValue").textContent =
        currentCharacter.currentHp + " / " + currentCharacter.maxHp;
}

function getHitDieValue(hitDie) {
    return Number(String(hitDie).replace("d", ""));
}

function getAverageHitDieValue(hitDie) {
    const hitDieValue = getHitDieValue(hitDie);

    if (hitDieValue === 6) {
        return 4;
    }

    if (hitDieValue === 8) {
        return 5;
    }

    if (hitDieValue === 10) {
        return 6;
    }

    if (hitDieValue === 12) {
        return 7;
    }

    return Math.ceil(hitDieValue / 2);
}

function calculateHp(hitDie, level, constitutionModifier) {
    const hitDieValue = getHitDieValue(hitDie);
    const averageHitDieValue = getAverageHitDieValue(hitDie);

    let hp = hitDieValue + constitutionModifier;

    for (let i = 2; i <= level; i++) {
        hp += averageHitDieValue + constitutionModifier;
    }

    if (hp < 1) {
        hp = 1;
    }

    return hp;
}

function downloadCharacter() {
    if (currentCharacter === null) {
        return;
    }

    updateCharacterFromInputs();

    currentCharacter.raceId =
        Number(document.getElementById("raceSelect").value);

    currentCharacter.classId =
        Number(document.getElementById("classSelect").value);

    currentCharacter.backgroundId =
        Number(document.getElementById("backgroundSelect").value);

    currentCharacter.level =
        Number(document.getElementById("levelInput").value) || 1;

    const data = JSON.stringify(currentCharacter, null, 4);

    const file = new Blob([data], {
        type: "application/json"
    });

    const link = document.createElement("a");

    link.href = URL.createObjectURL(file);
    link.download = "character.json";

    link.click();
}