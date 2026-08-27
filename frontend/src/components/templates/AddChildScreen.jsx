import React, { useState, useEffect } from 'react';
import InputField from '../atoms/InputField';
import AvatarPicker from '../atoms/AvatarPicker';
import Button from '../atoms/Button';
import BrandLogo from '../molecules/BrandLogo';
import { getEducationSystems, getAvailableLevels, getLevelLabel } from '../../utils/levels';
import { curriculumAPI } from '../../services/api';

export default function AddChildScreen({ parentName = 'Parent', onNavigate, onAddChild }) {
  const [name, setName] = useState('');
  const [age, setAge] = useState(9);
  const [educationSystem, setEducationSystem] = useState('UK');
  const [level, setLevel] = useState(4);
  const [avatar, setAvatar] = useState('🦁');
  const [profileImage, setProfileImage] = useState(null);
  const [enableStudentLogin, setEnableStudentLogin] = useState(false);
  const [studentEmail, setStudentEmail] = useState('');
  const [studentPassword, setStudentPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formError, setFormError] = useState('');
  const [availableSubjects, setAvailableSubjects] = useState([]);
  const [selectedSubjectIds, setSelectedSubjectIds] = useState([]);
  const [subjectsLoading, setSubjectsLoading] = useState(true);
  const [subjectsError, setSubjectsError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchSubjects() {
      try {
        setSubjectsError('');
        const res = await curriculumAPI.getSubjects();
        if (res.data) {
          setAvailableSubjects(res.data);
          // Default enroll in Mathematics, English Language, Science
          const defaultIds = res.data
            .filter((s) => ['mathematics', 'english-language', 'science'].includes(s.slug))
            .map((s) => s.id);
          setSelectedSubjectIds(defaultIds);
          if (res.data.length === 0) {
            setSubjectsError('Curriculum subjects are not configured yet. Please ask an administrator to import the curriculum first.');
          }
        }
      } catch (err) {
        console.error('Failed to load subjects:', err);
        setSubjectsError('Subjects could not be loaded. Please try again shortly.');
      } finally {
        setSubjectsLoading(false);
      }
    }
    fetchSubjects();
  }, []);

  const handleEducationSystemChange = (e) => {
    const newSys = e.target.value;
    setEducationSystem(newSys);
  };

  const handleSubjectToggle = (subjId) => {
    setSelectedSubjectIds((prev) =>
      prev.includes(subjId) ? prev.filter((id) => id !== subjId) : [...prev, subjId]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setFormError('');
    if (enableStudentLogin && (!studentEmail.trim() || studentPassword.length < 8 || studentPassword !== confirmPassword)) {
      setFormError('Enter a valid student email, matching passwords, and at least 8 characters.');
      return;
    }
    if (profileImage && profileImage.size > 5 * 1024 * 1024) {
      setFormError('Profile picture must be 5 MB or smaller.');
      return;
    }
    setLoading(true);
    try {
      await onAddChild({
        name: name.trim(), age: Number(age), education_system: educationSystem,
        level: Number(level), grade: getLevelLabel(level, educationSystem),
        subject_ids: selectedSubjectIds, avatar, profile_image: profileImage,
        student_email: enableStudentLogin ? studentEmail.trim() : null,
        student_password: enableStudentLogin ? studentPassword : null,
      });
    } catch (err) {
      setFormError(err.response?.data?.detail || 'The child profile could not be created.');
    } finally {
      setLoading(false);
    }
  };

  const educationSystems = getEducationSystems();
  const availableLevels = getAvailableLevels(educationSystem);
  const initial = parentName?.[0]?.toUpperCase() || 'P';

  return (
    <div className="screen active" id="addchild">
      <div className="app">
        <div className="appbar">
          <div className="wrap">
            <BrandLogo onClick={() => onNavigate('/')} />
            <div className="appbar-right">
              <div className="plan-tag">✨ Premium trial</div>
              <div className="avatar-btn">{initial}</div>
            </div>
          </div>
        </div>

        <div className="wrap" style={{ maxWidth: 580, paddingTop: 24, paddingBottom: 56 }}>
          <div style={{ textAlign: 'center', marginBottom: 26 }}>
            <div style={{ fontSize: 46 }}>👋</div>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 6 }}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => onNavigate('/parent')} style={{ position: 'absolute', left: 24 }}>← Back</button>
              <h1 style={{ fontSize: 30, color: 'var(--plum)' }}>Add your child</h1>
            </div>
            <p style={{ color: 'var(--ink-soft)', fontWeight: 600, marginTop: 4 }}>
              Configure their education system, level, and academic pathway.
            </p>
          </div>

          <div className="card pad">
            <form onSubmit={handleSubmit}>
              {formError && <div style={{ background: '#FFF1F0', color: '#DC2626', padding: '10px 14px', borderRadius: 10, fontSize: 13, fontWeight: 700, marginBottom: 14 }}>{formError}</div>}
              <InputField
                label="Child's name"
                placeholder="e.g. Mayowa, Johnson, Leo"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />

              <InputField
                label="Age"
                type="number"
                value={age}
                onChange={(e) => setAge(Number(e.target.value))}
                required
              />

              <div className="field">
                <label>Education System / Country</label>
                <select value={educationSystem} onChange={handleEducationSystemChange}>
                  {educationSystems.map((sys) => (
                    <option key={sys.id} value={sys.id}>
                      {sys.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label>Student Level ({educationSystem})</label>
                <select value={level} onChange={(e) => setLevel(Number(e.target.value))}>
                  {availableLevels.map((lvl) => (
                    <option key={lvl.level} value={lvl.level}>
                      {lvl.label} (Level {lvl.level})
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label>Academic Pathway Subjects</label>
                <p style={{ fontSize: 13, color: 'var(--ink-soft)', marginBottom: 8, fontWeight: 500 }}>
                  Select the subjects your child will study:
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 8 }}>
                  {availableSubjects.map((subj) => {
                    const isSelected = selectedSubjectIds.includes(subj.id);
                    return (
                      <div
                        key={subj.id}
                        onClick={() => handleSubjectToggle(subj.id)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '8px 12px',
                          borderRadius: 10,
                          border: isSelected ? '2px solid var(--plum)' : '1px solid var(--line)',
                          background: isSelected ? 'var(--cream)' : '#fff',
                          cursor: 'pointer',
                          userSelect: 'none',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        <span style={{ fontSize: 18 }}>{subj.icon}</span>
                        <span style={{ fontSize: 13, fontWeight: isSelected ? 700 : 500, color: 'var(--plum)' }}>
                          {subj.title}
                        </span>
                      </div>
                    );
                  })}
                </div>
                {subjectsLoading && <p style={{ fontSize: 13, color: 'var(--ink-soft)' }}>Loading subjects…</p>}
                {subjectsError && <div className="admin-notice" style={{ marginTop: 8 }}>{subjectsError}</div>}
              </div>

              <div className="field" style={{ marginTop: 16 }}>
                <label>Pick an avatar</label>
                <AvatarPicker selected={avatar} onSelect={setAvatar} />
              </div>

              <div className="field">
                <label>Profile picture (optional)</label>
                <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setProfileImage(e.target.files?.[0] || null)} />
                <p style={{ fontSize: 12, color: 'var(--ink-soft)', marginTop: 5 }}>JPEG, PNG or WebP · maximum 5 MB. The avatar remains as fallback.</p>
              </div>

              <div className="field" style={{ marginTop: 16 }}>
                <label className="student-login-toggle">
                  <input type="checkbox" checked={enableStudentLogin} onChange={(e) => setEnableStudentLogin(e.target.checked)} />
                  Allow this student to log in directly
                </label>
              </div>
              {enableStudentLogin && <>
                <InputField label="Student email" type="email" value={studentEmail} onChange={(e) => setStudentEmail(e.target.value)} required />
                <InputField label="Student password" type="password" value={studentPassword} onChange={(e) => setStudentPassword(e.target.value)} required />
                <InputField label="Confirm student password" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />
                <p style={{ fontSize: 12, color: 'var(--ink-soft)', marginTop: -8, marginBottom: 12 }}>Passwords are securely hashed and cannot be viewed after saving.</p>
              </>}

              <Button type="submit" variant="primary" style={{ width: '100%', marginTop: 12 }} disabled={loading || subjectsLoading || availableSubjects.length === 0}>
                {loading ? 'Creating child...' : 'Create child →'}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
