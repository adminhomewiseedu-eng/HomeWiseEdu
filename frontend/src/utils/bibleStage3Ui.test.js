import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const app = read('../App.jsx');
const landing = read('../components/templates/LandingScreen.jsx');
const login = read('../components/templates/LoginScreen.jsx');
const signup = read('../components/templates/SignupScreen.jsx');
const bibleSignup = read('../components/templates/BibleSignupScreen.jsx');
const addChild = read('../components/templates/AddChildScreen.jsx');
const parent = read('../components/templates/ParentDashboardScreen.jsx');
const student = read('../components/templates/StudentDashboardScreen.jsx');
const api = read('../services/api.js');
const navbar = read('../components/organisms/Navbar.jsx');
const css = read('../index.css');

test('landing provides separate homeschool and Bible Study registration choices', () => {
  assert.match(landing, /Choose Full Homeschool/);
  assert.match(landing, /Choose Bible Study/);
  assert.match(landing, /Free during testing/);
  assert.match(landing, /\/bible-study\/signup/);
  assert.match(landing, /id="programmes"/);
  assert.match(landing, /scrollToProgrammes/);
  assert.match(landing, /tabIndex="-1"/);
  assert.doesNotMatch(landing, /Get started[\s\S]{0,120}onNavigate\(['"]signup/);
});

test('landing compact navigation preserves destinations and accessible menu behavior', () => {
  assert.match(landing, /landing-nav-desktop/);
  assert.match(landing, /landing-nav-compact/);
  assert.match(landing, /id="landing-mobile-menu"/);
  assert.match(landing, /aria-expanded=\{menuOpen\}/);
  assert.match(landing, /aria-controls="landing-mobile-menu"/);
  assert.match(landing, /Open navigation menu/);
  assert.match(landing, /event\.key === 'Escape'/);
  assert.match(landing, /window\.innerWidth > 960/);
  assert.match(landing, /closeMenuAndRun\(\(\) => scrollToId\('features'\)\)/);
  assert.match(landing, /closeMenuAndRun\(\(\) => scrollToId\('how'\)\)/);
  assert.match(landing, /closeMenuAndRun\(\(\) => scrollToId\('pricing'\)\)/);
  assert.match(landing, /closeMenuAndRun\(\(\) => onNavigate\('\/login'\)\)/);
  assert.match(landing, /closeMenuAndRun\(scrollToProgrammes\)/);
  assert.match(landing, /pendingMenuActionRef/);
  assert.match(landing, /useLayoutEffect/);
  assert.match(landing, /header\?\.getBoundingClientRect\(\)\.height/);
  assert.match(landing, /scrollMarginBlockStart = `\$\{headerHeight\}px`/);
  assert.match(landing, /scrollIntoView\(\{ behavior: 'smooth', block: 'start' \}\)/);
  assert.match(landing, /focus\(\{ preventScroll: true \}\)/);
  assert.match(css, /\.landing-nav-compact,.landing-mobile-menu\{ display:none; \}/);
  assert.match(css, /@media\(max-width:960px\)[\s\S]*\.landing-nav-desktop\{ display:none; \}[\s\S]*\.landing-nav-compact\{ display:flex/);
  assert.match(css, /\.landing-mobile-menu\{[^}]*border-radius:18px[^}]*linear-gradient[^}]*box-shadow/);
  assert.match(css, /\.landing-mobile-menu>\.landing-mobile-link\{[^}]*min-height:46px/);
  assert.match(css, /@media\(max-width:430px\)[\s\S]*\.landing-compact-cta\{ display:none; \}/);
});

test('Bible registration uses its dedicated server-owned endpoint and onboarding route', () => {
  assert.match(api, /\/api\/auth\/register\/bible-study/);
  assert.match(app, /path="\/bible-study\/signup"/);
  assert.match(app, /go\('\/bible-study\/add-child'\)/);
  assert.match(signup, /Create Bible Study account/);
  assert.match(app, /standaloneAuthPages\.includes\(currentPath\)/);
  assert.match(app, /'bible-study\/signup'/);
  assert.match(navbar, /replace\(\/\^\\\/\+\|\\\/\+\$\/g, ''\)/);
});

test('shared authentication layout is split on desktop and form-only on compact screens', () => {
  assert.match(login, /<AuthVisualSide/);
  assert.match(signup, /<AuthVisualSide/);
  assert.match(bibleSignup, /<SignupScreen \{\.\.\.props\} bibleStudy \/>/);
  assert.match(css, /\.auth-wrap\{ min-height:100vh; display:grid; grid-template-columns:1fr 1fr; \}/);
  assert.match(css, /@media\(max-width:960px\)[\s\S]*\.auth-wrap\{[^}]*grid-template-columns:minmax\(0,1fr\)[^}]*\}/);
  assert.match(css, /@media\(max-width:960px\)[\s\S]*\.auth-visual\{ display:none; \}/);
  assert.match(css, /@media\(max-width:960px\)[\s\S]*\.auth-form-side\{[^}]*width:100%[^}]*min-width:0[^}]*min-height:100svh[^}]*\}/);
  assert.match(css, /@media\(max-width:768px\)[\s\S]*\.auth-form-side\{[^}]*align-items:flex-start[^}]*padding:24px 20px 36px[^}]*\}/);
  assert.match(css, /@media\(max-width:768px\)[\s\S]*\.auth-card\{ max-width:500px; \}/);
  assert.doesNotMatch(css, /@media\(max-width:768px\)[\s\S]*\.auth-visual\{ min-height:190px/);
});

test('Bible child onboarding hides general subject selection and relies on backend enrollment', () => {
  assert.match(addChild, /!bibleStudy && <div className="field">\s*<label>Academic Pathway Subjects/);
  assert.match(addChild, /Understanding The Word/);
  assert.match(addChild, /\.\.\(bibleStudy \? \{\} : \{ subject_ids: selectedSubjectIds \}\)/);
  assert.match(addChild, /student_email/);
  assert.match(addChild, /profile_image/);
});

test('programme-aware routes isolate Bible and homeschool dashboards', () => {
  assert.match(app, /path="\/bible-study\/parent"/);
  assert.match(app, /path="\/bible-study\/student"/);
  assert.match(app, /mayOpenProgrammeRoute\(currentUser, 'homeschool'\)/);
  assert.match(app, /isBibleUser\(currentUser\)/);
});

test('Bible dashboards provide focused parent and student states without duplicating learning', () => {
  assert.match(parent, /Understanding The Word journey/);
  assert.match(parent, /!bibleStudy/);
  assert.match(student, /bibleSubjectsOnly/);
  assert.match(student, /Understanding The Word is being prepared for your level/);
  assert.match(app, /<LessonPlayerScreen/);
  assert.match(app, /<QuizScreen/);
});
