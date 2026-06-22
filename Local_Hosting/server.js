const express = require("express");
const cors = require("cors");
const { Pool } = require("pg");
require("dotenv").config();

const app = express();

const PORT = process.env.SERVER_PORT || 3001;

app.use(cors());
app.use(express.json());

const pool = new Pool({
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    database: process.env.DB_NAME,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD
});

app.get("/api/test-db", async (req, res) => {
    try {
        const result = await pool.query("SELECT NOW() AS current_time");

        res.json({
            message: "Подключение к PostgreSQL работает",
            database: process.env.DB_NAME,
            time: result.rows[0].current_time
        });
    } catch (error) {
        res.status(500).json({
            message: "Ошибка подключения к PostgreSQL",
            error: error.message
        });
    }
});

app.get("/api/races", async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT id, name, description, speed
            FROM races
            ORDER BY name
        `);

        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get("/api/subraces", async (req, res) => {
    try {
        const { raceId } = req.query;

        let result;

        if (raceId) {
            result = await pool.query(`
                SELECT id, name, description, race_id
                FROM subraces
                WHERE race_id = $1
                ORDER BY name
            `, [raceId]);
        } else {
            result = await pool.query(`
                SELECT id, name, description, race_id
                FROM subraces
                ORDER BY name
            `);
        }

        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get("/api/classes", async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT id, name, description, hit_die
            FROM classes
            ORDER BY name
        `);

        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get("/api/subclasses", async (req, res) => {
    try {
        const { classId } = req.query;

        let result;

        if (classId) {
            result = await pool.query(`
                SELECT id, name, description, class_id
                FROM subclasses
                WHERE class_id = $1
                ORDER BY name
            `, [classId]);
        } else {
            result = await pool.query(`
                SELECT id, name, description, class_id
                FROM subclasses
                ORDER BY name
            `);
        }

        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get("/api/backgrounds", async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT id, name, description, feature_name, feature_description
            FROM backgrounds
            ORDER BY name
        `);

        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get("/api/spells", async (req, res) => {
    try {
        const { classId, level } = req.query;

        const conditions = [];
        const params = [];

        if (classId) {
            params.push(classId);
            conditions.push(`c.id = $${params.length}`);
        }

        if (level !== undefined && level !== "") {
            params.push(Number(level));
            conditions.push(`sp.level = $${params.length}`);
        }

        const whereSql = conditions.length > 0
            ? `WHERE ${conditions.join(" AND ")}`
            : "";

        const result = await pool.query(`
            SELECT
                sp.id,
                sp.name,
                sp.level,
                ms.name AS school,
                sp.casting_time,
                sp."range",
                sp.components,
                sp.material_components,
                sp.duration,
                sp.description,
                sp.higher_levels,
                sp.is_ritual,
                sp.is_concentration,
                STRING_AGG(DISTINCT c.name, ', ' ORDER BY c.name) AS classes
            FROM spells sp
            LEFT JOIN magic_schools ms ON ms.id = sp.school_id
            LEFT JOIN spell_classes sc ON sc.spell_id = sp.id
            LEFT JOIN classes c ON c.id = sc.class_id
            ${whereSql}
            GROUP BY
                sp.id,
                sp.name,
                sp.level,
                ms.name,
                sp.casting_time,
                sp."range",
                sp.components,
                sp.material_components,
                sp.duration,
                sp.description,
                sp.higher_levels,
                sp.is_ritual,
                sp.is_concentration
            ORDER BY sp.level, sp.name
        `, params);

        res.json(result.rows);
    } catch (error) {
        console.error("Ошибка загрузки заклинаний:", error);
        res.status(500).json({ error: error.message });
    }
});

app.get("/api/equipment", async (req, res) => {
    try {
        const { categoryId, classId } = req.query;

        if (classId) {
            const result = await pool.query(`
                SELECT
                    e.id,
                    e.name,
                    ec.name AS category,
                    e.cost_value,
                    e.cost_coin,
                    e.weight,
                    e.description,
                    cse.quantity
                FROM class_starting_equipment cse
                JOIN equipment e ON e.id = cse.equipment_id
                LEFT JOIN equipment_categories ec ON ec.id = e.category_id
                WHERE cse.class_id = $1
                ORDER BY ec.name, e.name
            `, [classId]);

            return res.json(result.rows);
        }

        let result;

        if (categoryId) {
            result = await pool.query(`
                SELECT
                    e.id,
                    e.name,
                    ec.name AS category,
                    e.cost_value,
                    e.cost_coin,
                    e.weight,
                    e.description
                FROM equipment e
                LEFT JOIN equipment_categories ec ON ec.id = e.category_id
                WHERE e.category_id = $1
                ORDER BY ec.name, e.name
            `, [categoryId]);
        } else {
            result = await pool.query(`
                SELECT
                    e.id,
                    e.name,
                    ec.name AS category,
                    e.cost_value,
                    e.cost_coin,
                    e.weight,
                    e.description
                FROM equipment e
                LEFT JOIN equipment_categories ec ON ec.id = e.category_id
                ORDER BY ec.name, e.name
            `);
        }

        res.json(result.rows);
    } catch (error) {
        console.error("Ошибка загрузки снаряжения:", error);
        res.status(500).json({ error: error.message });
    }
});

app.get("/api/equipment-categories", async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT id, name
            FROM equipment_categories
            ORDER BY name
        `);

        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get("/api/feats", async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT
                f.id,
                f.name,
                f.description,
                f.prerequisite,
                f.benefit,
                STRING_AGG(
                    DISTINCT
                    CASE
                        WHEN a.name IS NOT NULL THEN a.name || ' +' || fab.bonus
                        ELSE NULL
                    END,
                    ', '
                    ORDER BY
                    CASE
                        WHEN a.name IS NOT NULL THEN a.name || ' +' || fab.bonus
                        ELSE NULL
                    END
                ) AS ability_bonuses
            FROM feats f
            LEFT JOIN feat_ability_bonuses fab ON fab.feat_id = f.id
            LEFT JOIN ability_scores a ON a.id = fab.ability_score_id
            GROUP BY f.id, f.name, f.description, f.prerequisite, f.benefit
            ORDER BY f.name
        `);

        res.json(result.rows);
    } catch (error) {
        console.error("Ошибка загрузки черт:", error);
        res.status(500).json({ error: error.message });
    }
});

app.post("/api/generate-character", async (req, res) => {
    try {
        let { level } = req.body;

        level = Number(level) || 1;

        if (level < 1) {
            level = 1;
        }

        if (level > 20) {
            level = 20;
        }

        const raceResult = await pool.query(`
            SELECT id, name, description, speed
            FROM races
            ORDER BY RANDOM()
            LIMIT 1
        `);

        const classResult = await pool.query(`
            SELECT id, name, description, hit_die
            FROM classes
            ORDER BY RANDOM()
            LIMIT 1
        `);

        const backgroundResult = await pool.query(`
            SELECT id, name, description, feature_name, feature_description
            FROM backgrounds
            ORDER BY RANDOM()
            LIMIT 1
        `);

        if (raceResult.rows.length === 0) {
            return res.status(400).json({ error: "В таблице races нет данных" });
        }

        if (classResult.rows.length === 0) {
            return res.status(400).json({ error: "В таблице classes нет данных" });
        }

        if (backgroundResult.rows.length === 0) {
            return res.status(400).json({ error: "В таблице backgrounds нет данных" });
        }

        const race = raceResult.rows[0];
        const characterClass = classResult.rows[0];
        const background = backgroundResult.rows[0];

        const subraceResult = await pool.query(`
            SELECT id, name, description
            FROM subraces
            WHERE race_id = $1
            ORDER BY RANDOM()
            LIMIT 1
        `, [race.id]);

        const subrace = subraceResult.rows.length > 0 ? subraceResult.rows[0] : null;

        const abilities = generateAbilities();

        await applyRaceBonuses(abilities, race.id, subrace ? subrace.id : null);

        const constitutionModifier = getAbilityModifier(abilities["Телосложение"]);

        const maxHp = calculateHp(characterClass.hit_die, level, constitutionModifier);

        const proficiencyBonus = getProficiencyBonus(level);

        const characterSpells = await getRandomSpellsForClass(characterClass.id, level);

        const characterEquipment = await getStartingEquipmentForClass(characterClass.id);

        const characterFeats = await getRandomFeats(level);

        const character = {
            level: level,

            raceId: race.id,
            classId: characterClass.id,
            backgroundId: background.id,
            subraceId: subrace ? subrace.id : null,

            race: race.name,
            subrace: subrace ? subrace.name : null,
            class: characterClass.name,
            background: background.name,

            speed: race.speed,
            hitDie: characterClass.hit_die,
            maxHp: maxHp,
            currentHp: maxHp,
            proficiencyBonus: proficiencyBonus,

            abilities: abilities,

            modifiers: {
                "Сила": getAbilityModifier(abilities["Сила"]),
                "Ловкость": getAbilityModifier(abilities["Ловкость"]),
                "Телосложение": getAbilityModifier(abilities["Телосложение"]),
                "Интеллект": getAbilityModifier(abilities["Интеллект"]),
                "Мудрость": getAbilityModifier(abilities["Мудрость"]),
                "Харизма": getAbilityModifier(abilities["Харизма"])
            },

            backgroundFeature: {
                name: background.feature_name,
                description: background.feature_description
            },

            spells: characterSpells,
            equipment: characterEquipment,
            feats: characterFeats
        };

        res.json(character);
    } catch (error) {
        console.error("Ошибка генерации персонажа:", error);

        res.status(500).json({
            error: error.message
        });
    }
});

function rollD6() {
    return Math.floor(Math.random() * 6) + 1;
}

function rollAbilityScore() {
    const rolls = [rollD6(), rollD6(), rollD6(), rollD6()];

    rolls.sort((a, b) => b - a);

    return rolls[0] + rolls[1] + rolls[2];
}

function generateAbilities() {
    return {
        "Сила": rollAbilityScore(),
        "Ловкость": rollAbilityScore(),
        "Телосложение": rollAbilityScore(),
        "Интеллект": rollAbilityScore(),
        "Мудрость": rollAbilityScore(),
        "Харизма": rollAbilityScore()
    };
}

function getAbilityModifier(score) {
    return Math.floor((score - 10) / 2);
}

function getProficiencyBonus(level) {
    if (level >= 17) {
        return 6;
    }

    if (level >= 13) {
        return 5;
    }

    if (level >= 9) {
        return 4;
    }

    if (level >= 5) {
        return 3;
    }

    return 2;
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

async function applyRaceBonuses(abilities, raceId, subraceId) {
    const bonusesResult = await pool.query(`
        SELECT
            rab.id,
            rab.race_id,
            rab.subrace_id,
            rab.bonus,
            rab.is_choice,
            rab.choice_count,
            rab.description,
            a.name AS ability_name
        FROM race_ability_bonuses rab
        LEFT JOIN ability_scores a ON rab.ability_score_id = a.id
        WHERE rab.race_id = $1
           OR ($2::integer IS NOT NULL AND rab.subrace_id = $2)
        ORDER BY rab.is_choice, rab.id
    `, [raceId, subraceId]);

    const choiceGroups = new Map();

    for (const bonus of bonusesResult.rows) {
        if (bonus.is_choice === false && bonus.ability_name) {
            abilities[bonus.ability_name] += Number(bonus.bonus);
            continue;
        }

        if (bonus.is_choice === true && bonus.ability_name) {
            const groupKey = [
                bonus.race_id || "no-race",
                bonus.subrace_id || "no-subrace",
                bonus.bonus,
                bonus.choice_count,
                bonus.description || "choice"
            ].join("|");

            if (!choiceGroups.has(groupKey)) {
                choiceGroups.set(groupKey, {
                    bonus: Number(bonus.bonus),
                    choiceCount: Number(bonus.choice_count),
                    abilityNames: []
                });
            }

            choiceGroups.get(groupKey).abilityNames.push(bonus.ability_name);
        }
    }

    for (const group of choiceGroups.values()) {
        applyRandomChoiceBonusFromList(
            abilities,
            group.abilityNames,
            group.choiceCount,
            group.bonus
        );
    }
}

function applyRandomChoiceBonusFromList(abilities, availableAbilityNames, choiceCount, bonusValue) {
    const uniqueAbilities = [...new Set(availableAbilityNames)];

    const shuffled = uniqueAbilities.sort(() => Math.random() - 0.5);

    for (let i = 0; i < choiceCount && i < shuffled.length; i++) {
        const abilityName = shuffled[i];

        if (abilities[abilityName] !== undefined) {
            abilities[abilityName] += bonusValue;
        }
    }
}

function getMaxSpellLevel(characterLevel) {
    if (characterLevel >= 17) {
        return 9;
    }

    if (characterLevel >= 15) {
        return 8;
    }

    if (characterLevel >= 13) {
        return 7;
    }

    if (characterLevel >= 11) {
        return 6;
    }

    if (characterLevel >= 9) {
        return 5;
    }

    if (characterLevel >= 7) {
        return 4;
    }

    if (characterLevel >= 5) {
        return 3;
    }

    if (characterLevel >= 3) {
        return 2;
    }

    return 1;
}

async function getRandomSpellsForClass(classId, level) {
    const maxSpellLevel = getMaxSpellLevel(level);

    const result = await pool.query(`
        SELECT
            sp.id,
            sp.name,
            sp.level,
            ms.name AS school,
            sp.casting_time,
            sp."range",
            sp.components,
            sp.duration
        FROM spells sp
        JOIN spell_classes sc ON sc.spell_id = sp.id
        LEFT JOIN magic_schools ms ON ms.id = sp.school_id
        WHERE sc.class_id = $1
          AND sp.level <= $2
        ORDER BY RANDOM()
        LIMIT 8
    `, [classId, maxSpellLevel]);

    return result.rows;
}

async function getStartingEquipmentForClass(classId) {
    const result = await pool.query(`
        SELECT
            e.id,
            e.name,
            ec.name AS category,
            e.cost_value,
            e.cost_coin,
            e.weight,
            e.description,
            cse.quantity
        FROM class_starting_equipment cse
        JOIN equipment e ON e.id = cse.equipment_id
        LEFT JOIN equipment_categories ec ON ec.id = e.category_id
        WHERE cse.class_id = $1
        ORDER BY ec.name, e.name
    `, [classId]);

    return result.rows;
}

async function getRandomFeats(level) {
    if (level < 4) {
        return [];
    }

    const result = await pool.query(`
        SELECT
            f.id,
            f.name,
            f.description,
            f.prerequisite,
            f.benefit
        FROM feats f
        ORDER BY RANDOM()
        LIMIT 1
    `);

    return result.rows;
}

app.get("/", (req, res) => {
    res.send("Backend работает. Для проверки БД открой /api/test-db");
});

app.listen(PORT, () => {
    console.log(`Backend запущен: http://localhost:${PORT}`);
});