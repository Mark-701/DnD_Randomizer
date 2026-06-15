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

app.post("/api/generate-character", async (req, res) => {
    try {
        let { level } = req.body;

        // Если уровень не передали, персонаж будет 1 уровня
        level = Number(level) || 1;

        // Ограничиваем уровень правилами D&D: от 1 до 20
        if (level < 1) {
            level = 1;
        }

        if (level > 20) {
            level = 20;
        }

        // Случайная раса
        const raceResult = await pool.query(`
            SELECT id, name, description, speed
            FROM races
            ORDER BY RANDOM()
            LIMIT 1
        `);

        // Случайный класс
        const classResult = await pool.query(`
            SELECT id, name, description, hit_die
            FROM classes
            ORDER BY RANDOM()
            LIMIT 1
        `);

        // Случайная предыстория
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

        // Случайная подраса, если она есть у выбранной расы
        const subraceResult = await pool.query(`
            SELECT id, name, description
            FROM subraces
            WHERE race_id = $1
            ORDER BY RANDOM()
            LIMIT 1
        `, [race.id]);

        const subrace = subraceResult.rows.length > 0 ? subraceResult.rows[0] : null;

        // Генерация характеристик по правилам D&D
        const abilities = generateAbilities();

        // Применяем расовые и подрасовые бонусы
        await applyRaceBonuses(abilities, race.id, subrace ? subrace.id : null);

        // Модификатор Телосложения
        const constitutionModifier = getAbilityModifier(abilities["Телосложение"]);

        // Максимум здоровья
        const maxHp = calculateHp(characterClass.hit_die, level, constitutionModifier);

        // Бонус мастерства
        const proficiencyBonus = getProficiencyBonus(level);

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
            }
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

// 4d6 drop lowest:
// бросаем 4 шестигранных кубика,
// убираем самый маленький,
// складываем оставшиеся 3
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

// Модификатор характеристики:
// 10–11 = 0
// 12–13 = +1
// 8–9 = -1
function getAbilityModifier(score) {
    return Math.floor((score - 10) / 2);
}

// Бонус мастерства по уровню
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

// Превращаем строку 'd6', 'd8', 'd10', 'd12' в число
function getHitDieValue(hitDie) {
    return Number(String(hitDie).replace("d", ""));
}

// Среднее значение кости хитов при повышении уровня
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

// HP:
// 1 уровень: максимум кости + CON
// следующие уровни: среднее кости + CON
function calculateHp(hitDie, level, constitutionModifier) {
    const hitDieValue = getHitDieValue(hitDie);
    const averageHitDieValue = getAverageHitDieValue(hitDie);

    let hp = hitDieValue + constitutionModifier;

    for (let i = 2; i <= level; i++) {
        hp += averageHitDieValue + constitutionModifier;
    }

    // Чтобы HP не стало меньше 1
    if (hp < 1) {
        hp = 1;
    }

    return hp;
}

// Применение бонусов расы и подрасы
async function applyRaceBonuses(abilities, raceId, subraceId) {
    const bonusesResult = await pool.query(`
        SELECT
            rab.bonus,
            rab.is_choice,
            rab.choice_count,
            a.name AS ability_name
        FROM race_ability_bonuses rab
        LEFT JOIN ability_scores a ON rab.ability_score_id = a.id
        WHERE rab.race_id = $1
           OR ($2::integer IS NOT NULL AND rab.subrace_id = $2)
        ORDER BY rab.id
    `, [raceId, subraceId]);

    for (const bonus of bonusesResult.rows) {
        // Обычный фиксированный бонус, например +2 к Ловкости
        if (bonus.is_choice === false && bonus.ability_name) {
            abilities[bonus.ability_name] += bonus.bonus;
        }

        // Бонус на выбор, например +1 к двум любым характеристикам
        // Так как пользователь не выбирает вручную, выбираем случайно
        if (bonus.is_choice === true) {
            applyRandomChoiceBonus(
                abilities,
                bonus.choice_count,
                bonus.bonus
            );
        }
    }
}

// Случайно выбирает характеристики для бонуса на выбор
function applyRandomChoiceBonus(abilities, choiceCount, bonusValue) {
    const abilityNames = Object.keys(abilities);

    let finalBonus = Number(bonusValue);

    if (finalBonus === 0) {
        finalBonus = 1;
    }

    const shuffled = abilityNames.sort(() => Math.random() - 0.5);

    for (let i = 0; i < choiceCount && i < shuffled.length; i++) {
        abilities[shuffled[i]] += finalBonus;
    }
}

app.get("/", (req, res) => {
    res.send("Backend работает. Для проверки БД открой /api/test-db");
});

app.listen(PORT, () => {
    console.log(`Backend запущен: http://localhost:${PORT}`);
});