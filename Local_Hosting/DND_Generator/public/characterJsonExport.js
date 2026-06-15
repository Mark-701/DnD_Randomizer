function downloadCharacterJson(character, updateCharacterCallback) {
    if (character === null) {
        return;
    }

    if (typeof updateCharacterCallback === "function") {
        updateCharacterCallback();
    }

    const exportObject = buildLssCharacterJson(character);

    const data = JSON.stringify(exportObject, null, 2);

    const file = new Blob([data], {
        type: "application/json"
    });

    const link = document.createElement("a");

    link.href = URL.createObjectURL(file);
    link.download = "character.json";

    link.click();

    URL.revokeObjectURL(link.href);
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
        spells: {
            mode: "cards",
            prepared: [],
            book: []
        },
        data: JSON.stringify(innerData),
        jsonType: "character",
        version: "2"
    };
}


function buildCharacterData(character) {
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

        spellsInfo: {
            base: {
                name: "base",
                value: ""
            },
            save: {
                name: "save",
                value: ""
            },
            mod: {
                name: "mod",
                value: ""
            }
        },

        spells: {},
        spellsPact: {},

        proficiency: character.proficiencyBonus || 2,

        stats: buildStats(character),
        saves: buildSaves(),
        skills: buildSkills(),

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
                value: makeTextDocument(buildBackgroundFeatureText(character))
            },
            prof: {
                value: makeTextDocument("")
            },
            equipment: {
                value: makeTextDocument(buildEquipmentText(character))
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
    const modifier = getCharacterJsonAbilityModifier(value);

    return {
        name: name,
        score: value,
        modifier: modifier,
        check: modifier
    };
}


function getCharacterJsonAbilityModifier(score) {
    return Math.floor((score - 10) / 2);
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
            if (item.quantity && item.quantity > 1) {
                return item.name + " x" + item.quantity;
            }

            return item.name;
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