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

        renderCharacterSpells(currentCharacter.spells || []);
        renderCharacterEquipment(currentCharacter.equipment || []);
        renderCharacterFeats(currentCharacter.feats || []);

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

    const exportObject = buildLssCharacterJson(currentCharacter);

    const data = JSON.stringify(exportObject, null, 2);

    const file = new Blob([data], {
        type: "application/json"
    });

    const link = document.createElement("a");

    link.href = URL.createObjectURL(file);
    link.download = "character.json";

    link.click();
}

function buildLssCharacterJson(character) {
    const innerData = buildCharacterData(character);

    return {
        tags: [],
        disabledBlocks: {
            "info-left": [],
            "info-right": [],
            "subinfo-left": [],
            "subinfo-right": [],
            "notes-left": [],
            "notes-right": [],
            "_id": generateId()
        },
        edition: "2024",

        // Заклинания для Long Story Short
        spells: buildLssSpellsBlock(character),

        data: JSON.stringify(innerData),
        jsonType: "character",
        version: "2"
    };
}

function buildCharacterData(character) {
    const stats = buildStats(character);
    const skills = buildSkills();
    const saves = buildSaves();

    return {
        isDefault: true,
        jsonType: "character",
        template: "default",

        name: {
            value: character.name || "Без имени"
        },

        info: {
            charClass: {
                name: "charClass",
                value: character.class || ""
            },
            charSubclass: {
                name: "charSubclass",
                value: character.subclass || ""
            },
            level: {
                name: "level",
                value: character.level || 1
            },
            background: {
                name: "background",
                value: character.background || ""
            },
            playerName: {
                name: "playerName",
                value: ""
            },
            race: {
                name: "race",
                value: character.subrace
                    ? character.race + " (" + character.subrace + ")"
                    : character.race || ""
            },
            alignment: {
                name: "alignment",
                value: ""
            },
            experience: {
                name: "experience",
                value: 0
            }
        },

        subInfo: {
            age: {
                name: "age",
                value: ""
            },
            height: {
                name: "height",
                value: ""
            },
            weight: {
                name: "weight",
                value: ""
            },
            eyes: {
                name: "eyes",
                value: ""
            },
            skin: {
                name: "skin",
                value: ""
            },
            hair: {
                name: "hair",
                value: ""
            }
        },

        spellsInfo: buildSpellsInfo(character),

        // Дублируем заклинания внутрь data.
        // Даже если Long Story Short не примет карточки,
        // список заклинаний всё равно останется внутри персонажа.
        spells: buildInnerSpellsMap(character),
        spellsPact: {},

        proficiency: character.proficiencyBonus || 2,

        stats: stats,
        saves: saves,
        skills: skills,

        vitality: {
            "hp-dice-current": {
                value: character.level || 1
            },
            "hp-dice-multi": {},
            ac: {
                value: 10
            },
            initiative: {
                value: null
            },
            speed: {
                value: character.speed || 30
            },
            "hit-die": {
                value: character.hitDie || ""
            },
            "hp-max": {
                value: character.maxHp || 1
            },
            isDying: false,
            "hp-current": {
                value: character.currentHp || character.maxHp || 1
            },
            "hp-temp": {
                value: 0
            },
            deathFails: 0,
            deathSuccesses: 0,
            shield: {
                value: false,
                mod: 0
            }
        },

        attunementsList: [
            {
                id: "attunement-" + Date.now(),
                checked: false,
                value: ""
            }
        ],

        weaponsList: [],
        weapons: {},

        text: {
            traits: {
                value: makeTextDocument("")
            },
            background: {
                value: makeTextDocument(character.backgroundDescription || "")
            },
            features: {
            value: makeTextDocument(
            buildFeaturesText(character)
            )
            },
            prof: {
                value: makeTextDocument("")
            },
            equipment: {
                value: makeTextDocument(
                    buildEquipmentText(character)
                )
            },
            appearance: {
                value: makeTextDocument("")
            }
        },

        coins: {
            gp: {
                value: 0
            },
            total: {
                value: 0
            },
            sp: {
                value: 0
            },
            cp: {
                value: 0
            },
            pp: {
                value: 0
            },
            ep: {
                value: 0
            }
        },

        resources: {},
        bonusesSkills: {},
        bonusesStats: {},
        conditions: [],

        createdAt: new Date().toISOString(),

        avatar: {},
        inspiration: false
    };
}

function buildStats(character) {
    return {
        str: buildStat("str", character.abilities["Сила"]),
        dex: buildStat("dex", character.abilities["Ловкость"]),
        con: buildStat("con", character.abilities["Телосложение"]),
        int: buildStat("int", character.abilities["Интеллект"]),
        wis: buildStat("wis", character.abilities["Мудрость"]),
        cha: buildStat("cha", character.abilities["Харизма"])
    };
}

function buildStat(name, score) {
    const value = Number(score) || 10;
    const modifier = getAbilityModifier(value);

    return {
        name: name,
        score: value,
        modifier: modifier,
        check: modifier
    };
}

function buildSaves() {
    return {
        str: {
            name: "str",
            isProf: false
        },
        dex: {
            name: "dex",
            isProf: false
        },
        con: {
            name: "con",
            isProf: false
        },
        int: {
            name: "int",
            isProf: false
        },
        wis: {
            name: "wis",
            isProf: false
        },
        cha: {
            name: "cha",
            isProf: false
        }
    };
}

function buildSkills() {
    return {
        acrobatics: {
            baseStat: "dex",
            name: "acrobatics"
        },
        investigation: {
            baseStat: "int",
            name: "investigation"
        },
        athletics: {
            baseStat: "str",
            name: "athletics"
        },
        perception: {
            baseStat: "wis",
            name: "perception"
        },
        survival: {
            baseStat: "wis",
            name: "survival"
        },
        performance: {
            baseStat: "cha",
            name: "performance"
        },
        intimidation: {
            baseStat: "cha",
            name: "intimidation"
        },
        history: {
            baseStat: "int",
            name: "history"
        },
        "sleight of hand": {
            baseStat: "dex",
            name: "sleight of hand"
        },
        arcana: {
            baseStat: "int",
            name: "arcana"
        },
        medicine: {
            baseStat: "wis",
            name: "medicine"
        },
        deception: {
            baseStat: "cha",
            name: "deception"
        },
        nature: {
            baseStat: "int",
            name: "nature"
        },
        insight: {
            baseStat: "wis",
            name: "insight"
        },
        religion: {
            baseStat: "int",
            name: "religion"
        },
        stealth: {
            baseStat: "dex",
            name: "stealth"
        },
        persuasion: {
            baseStat: "cha",
            name: "persuasion"
        },
        "animal handling": {
            baseStat: "wis",
            name: "animal handling"
        }
    };
}

function makeTextDocument(text) {
    const safeText = text || "";

    if (safeText.trim() === "") {
        return {
            data: {
                type: "doc",
                content: [
                    {
                        type: "paragraph"
                    }
                ]
            }
        };
    }

    const paragraphs = safeText
        .split("\n")
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .map(line => {
            return {
                type: "paragraph",
                content: [
                    {
                        type: "text",
                        text: line
                    }
                ]
            };
        });

    return {
        data: {
            type: "doc",
            content: paragraphs
        }
    };
}

function buildBackgroundFeatureText(character) {
    if (!character.backgroundFeature) {
        return "";
    }

    const name = character.backgroundFeature.name || "";
    const description = character.backgroundFeature.description || "";

    if (!name && !description) {
        return "";
    }

    return name + ". " + description;
}

function buildEquipmentText(character) {
    if (!character.equipment || character.equipment.length === 0) {
        return "";
    }

    return character.equipment
        .map(item => {
            const parts = [];

            let name = item.name || "Без названия";

            if (item.quantity && Number(item.quantity) > 1) {
                name += " x" + item.quantity;
            }

            parts.push(name);

            if (item.category) {
                parts.push("Категория: " + item.category);
            }

            if (item.cost_value || item.cost_coin) {
                parts.push(
                    "Цена: " +
                    (item.cost_value || "—") +
                    " " +
                    (item.cost_coin || "")
                );
            }

            if (item.weight) {
                parts.push("Вес: " + item.weight);
            }

            if (item.description) {
                parts.push(item.description);
            }

            return parts.join(" | ");
        })
        .join("\n");
}

function generateId() {
    const chars = "abcdef0123456789";
    let result = "";

    for (let i = 0; i < 24; i++) {
        result += chars[Math.floor(Math.random() * chars.length)];
    }

    return result;
}

function buildLssSpellsBlock(character) {
    const spells = character.spells || [];

    return {
        mode: "cards",

        // Подготовленные заклинания.
        // Для простоты все сгенерированные заклинания считаем подготовленными.
        prepared: spells.map(spell => buildLssSpellCard(spell)),

        // Книга заклинаний.
        // Дублируем туда же, чтобы Long Story Short точно видел список.
        book: spells.map(spell => buildLssSpellCard(spell))
    };
}

function buildLssSpellCard(spell) {
    return {
        id: "spell-" + generateId(),

        name: spell.name || "Без названия",

        level: Number(spell.level) || 0,

        school: spell.school || "",

        castingTime: spell.casting_time || "",

        range: spell.range || "",

        components: spell.components || "",

        duration: spell.duration || "",

        description: spell.description || "",

        higherLevels: spell.higher_levels || "",

        ritual: Boolean(spell.is_ritual),

        concentration: Boolean(spell.is_concentration),

        prepared: true
    };
}

function buildSpellsInfo(character) {
    return {
        base: {
            name: "base",
            value: getSpellcastingAbility(character)
        },
        save: {
            name: "save",
            value: ""
        },
        mod: {
            name: "mod",
            value: ""
        }
    };
}

function getSpellcastingAbility(character) {
    const className = String(character.class || "").toLowerCase();

    if (
        className.includes("волшебник") ||
        className.includes("wizard")
    ) {
        return "Интеллект";
    }

    if (
        className.includes("жрец") ||
        className.includes("друид") ||
        className.includes("следопыт") ||
        className.includes("cleric") ||
        className.includes("druid") ||
        className.includes("ranger")
    ) {
        return "Мудрость";
    }

    if (
        className.includes("бард") ||
        className.includes("паладин") ||
        className.includes("чародей") ||
        className.includes("колдун") ||
        className.includes("bard") ||
        className.includes("paladin") ||
        className.includes("sorcerer") ||
        className.includes("warlock")
    ) {
        return "Харизма";
    }

    return "";
}

function buildInnerSpellsMap(character) {
    const spells = character.spells || [];
    const result = {};

    for (const spell of spells) {
        const id = "spell-" + generateId();

        result[id] = {
            id: id,
            name: spell.name || "Без названия",
            level: Number(spell.level) || 0,
            school: spell.school || "",
            casting_time: spell.casting_time || "",
            range: spell.range || "",
            components: spell.components || "",
            duration: spell.duration || "",
            description: spell.description || "",
            higher_levels: spell.higher_levels || "",
            is_ritual: Boolean(spell.is_ritual),
            is_concentration: Boolean(spell.is_concentration)
        };
    }

    return result;
}

function buildFeaturesText(character) {
    const parts = [];

    const backgroundText = buildBackgroundFeatureText(character);

    if (backgroundText) {
        parts.push(backgroundText);
    }

    const featsText = buildFeatsText(character);

    if (featsText) {
        parts.push("Черты:\n" + featsText);
    }

    const spellsText = buildSpellsText(character);

    if (spellsText) {
        parts.push("Заклинания:\n" + spellsText);
    }

    return parts.join("\n\n");
}

function buildSpellsText(character) {
    if (!character.spells || character.spells.length === 0) {
        return "";
    }

    return character.spells
        .map(spell => {
            const parts = [];

            parts.push(spell.name || "Без названия");

            if (spell.level !== undefined && spell.level !== null) {
                parts.push("ур. " + spell.level);
            }

            if (spell.school) {
                parts.push(spell.school);
            }

            if (spell.casting_time) {
                parts.push("Время: " + spell.casting_time);
            }

            if (spell.range) {
                parts.push("Дистанция: " + spell.range);
            }

            if (spell.components) {
                parts.push("Компоненты: " + spell.components);
            }

            if (spell.duration) {
                parts.push("Длительность: " + spell.duration);
            }

            return parts.join(" | ");
        })
        .join("\n");
}

function buildFeatsText(character) {
    if (!character.feats || character.feats.length === 0) {
        return "";
    }

    return character.feats
        .map(feat => {
            let text = feat.name || "Без названия";

            if (feat.prerequisite) {
                text += ". Требование: " + feat.prerequisite;
            }

            if (feat.description) {
                text += ". " + feat.description;
            }

            if (feat.benefit) {
                text += ". " + feat.benefit;
            }

            return text;
        })
        .join("\n");
}

function renderCharacterSpells(spells) {
    const block = document.getElementById("characterSpellsBlock");

    if (!block) {
        return;
    }

    if (!spells || spells.length === 0) {
        block.innerHTML = `<p class="empty-text">У персонажа нет заклинаний.</p>`;
        return;
    }

    block.innerHTML = "";

    for (const spell of spells) {
        const card = document.createElement("div");
        card.className = "extra-card";

        card.innerHTML = `
            <strong>${spell.name}</strong>
            <p>Уровень: ${spell.level ?? "—"}</p>
            <p>Школа: ${spell.school || "—"}</p>
            <p>Время накладывания: ${spell.casting_time || "—"}</p>
            <p>Дистанция: ${spell.range || "—"}</p>
            <p>Компоненты: ${spell.components || "—"}</p>
            <p>Длительность: ${spell.duration || "—"}</p>
        `;

        block.appendChild(card);
    }
}

function renderCharacterEquipment(equipment) {
    const block = document.getElementById("characterEquipmentBlock");

    if (!block) {
        return;
    }

    if (!equipment || equipment.length === 0) {
        block.innerHTML = `<p class="empty-text">У персонажа нет стартового снаряжения.</p>`;
        return;
    }

    block.innerHTML = "";

    for (const item of equipment) {
        const card = document.createElement("div");
        card.className = "extra-card";

        card.innerHTML = `
            <strong>${item.name}</strong>
            <p>Количество: ${item.quantity || 1}</p>
            <p>Категория: ${item.category || "—"}</p>
            <p>Цена: ${item.cost_value || "—"} ${item.cost_coin || ""}</p>
            <p>Вес: ${item.weight || "—"}</p>
            ${item.description ? `<p>${item.description}</p>` : ""}
        `;

        block.appendChild(card);
    }
}

function renderCharacterFeats(feats) {
    const block = document.getElementById("characterFeatsBlock");

    if (!block) {
        return;
    }

    if (!feats || feats.length === 0) {
        block.innerHTML = `<p class="empty-text">У персонажа нет черт.</p>`;
        return;
    }

    block.innerHTML = "";

    for (const feat of feats) {
        const card = document.createElement("div");
        card.className = "extra-card";

        card.innerHTML = `
            <strong>${feat.name}</strong>
            ${feat.prerequisite ? `<p>Требование: ${feat.prerequisite}</p>` : ""}
            ${feat.description ? `<p>${feat.description}</p>` : ""}
            ${feat.benefit ? `<p>${feat.benefit}</p>` : ""}
        `;

        block.appendChild(card);
    }
}