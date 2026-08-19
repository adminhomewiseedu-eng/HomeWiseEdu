export const EDUCATION_SYSTEMS = {
  UK: {
    name: 'United Kingdom (England / Wales)',
    levels: {
      0: 'Reception',
      1: 'Year 1',
      2: 'Year 2',
      3: 'Year 3',
      4: 'Year 4',
      5: 'Year 5',
      6: 'Year 6',
      7: 'Year 7',
      8: 'Year 8',
      9: 'Year 9',
      10: 'Year 10',
      11: 'Year 11',
      12: 'Year 12',
      13: 'Year 13',
    },
  },
  USA: {
    name: 'United States',
    levels: {
      0: 'Kindergarten',
      1: 'Grade 1',
      2: 'Grade 2',
      3: 'Grade 3',
      4: 'Grade 4',
      5: 'Grade 5',
      6: 'Grade 6',
      7: 'Grade 7',
      8: 'Grade 8',
      9: 'Grade 9',
      10: 'Grade 10',
      11: 'Grade 11',
      12: 'Grade 12',
      13: 'Grade 12+ (Post-Secondary)',
    },
  },
  Canada: {
    name: 'Canada',
    levels: {
      0: 'Kindergarten',
      1: 'Grade 1',
      2: 'Grade 2',
      3: 'Grade 3',
      4: 'Grade 4',
      5: 'Grade 5',
      6: 'Grade 6',
      7: 'Grade 7',
      8: 'Grade 8',
      9: 'Grade 9',
      10: 'Grade 10',
      11: 'Grade 11',
      12: 'Grade 12',
      13: 'Grade 12+',
    },
  },
  Australia: {
    name: 'Australia',
    levels: {
      0: 'Foundation / Prep',
      1: 'Year 1',
      2: 'Year 2',
      3: 'Year 3',
      4: 'Year 4',
      5: 'Year 5',
      6: 'Year 6',
      7: 'Year 7',
      8: 'Year 8',
      9: 'Year 9',
      10: 'Year 10',
      11: 'Year 11',
      12: 'Year 12',
      13: 'Year 12+',
    },
  },
};

export function getLevelLabel(level, educationSystem = 'UK') {
  const sysKey = (educationSystem || 'UK').toUpperCase();
  const sys = EDUCATION_SYSTEMS[sysKey] || EDUCATION_SYSTEMS.UK;
  const numLevel = Number(level);
  return sys.levels[numLevel] !== undefined ? sys.levels[numLevel] : `Level ${level}`;
}

export function getAvailableLevels(educationSystem = 'UK') {
  const sysKey = (educationSystem || 'UK').toUpperCase();
  const sys = EDUCATION_SYSTEMS[sysKey] || EDUCATION_SYSTEMS.UK;
  return Object.entries(sys.levels).map(([lvl, label]) => ({
    level: Number(lvl),
    label,
  }));
}

export function getEducationSystems() {
  return Object.entries(EDUCATION_SYSTEMS).map(([code, data]) => ({
    id: code,
    name: data.name,
  }));
}
