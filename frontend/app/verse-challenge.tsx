import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Animated,
  StatusBar,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuthContext } from '../contexts/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

const DIFFICULTIES = [
  { value: 'easy', label: 'Easy', color: '#4ECDC4', icon: 'leaf' },
  { value: 'medium', label: 'Medium', color: '#FFD93D', icon: 'flame' },
  { value: 'hard', label: 'Hard', color: '#FF6B6B', icon: 'flash' },
] as const;

interface Challenge {
  date: string;
  reference: string;
  theme: string;
  difficulty: string;
  display_text: string;
  blank_count: number;
  full_verse: string;
}

interface SubmitResult {
  score: number;
  correct: number;
  total: number;
  results: { expected: string; given: string; correct: boolean }[];
  message: string;
  streak: number;
  full_verse: string;
  reference: string;
}

interface Stats {
  total_played: number;
  current_streak: number;
  best_streak: number;
  average_score: number;
  perfect_scores: number;
}

export default function VerseChallengeScreen() {
  const { activeChild } = useAuthContext();
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [answers, setAnswers] = useState<string[]>([]);
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [difficulty, setDifficulty] = useState('auto');

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const resultAnim = useRef(new Animated.Value(0)).current;

  const ageTier = activeChild?.age_tier || '7-9';
  const childId = activeChild?.child_id || 'guest_child';

  useEffect(() => {
    fetchChallenge();
    fetchStats();
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
      Animated.spring(scaleAnim, { toValue: 1, tension: 50, friction: 7, useNativeDriver: true }),
    ]).start();
  }, [difficulty]);

  const fetchChallenge = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/verse-challenge?age_tier=${ageTier}&difficulty=${difficulty}`);
      if (res.ok) {
        const data: Challenge = await res.json();
        setChallenge(data);
        setAnswers(new Array(data.blank_count).fill(''));
      }
    } catch (e) {
      console.log('Challenge fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/verse-challenge/stats/${childId}`);
      if (res.ok) {
        setStats(await res.json());
      }
    } catch (e) {
      console.log('Stats fetch error:', e);
    }
  };

  const handleSubmit = async () => {
    if (!challenge || answers.some(a => !a.trim())) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/verse-challenge/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          child_id: childId,
          answers,
          difficulty: challenge.difficulty,
        }),
      });
      if (res.ok) {
        const data: SubmitResult = await res.json();
        setResult(data);
        fetchStats();
        resultAnim.setValue(0);
        Animated.spring(resultAnim, { toValue: 1, tension: 50, friction: 6, useNativeDriver: true }).start();
      }
    } catch (e) {
      console.log('Submit error:', e);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetry = () => {
    setResult(null);
    if (challenge) setAnswers(new Array(challenge.blank_count).fill(''));
  };

  const updateAnswer = (index: number, value: string) => {
    setAnswers(prev => { const n = [...prev]; n[index] = value; return n; });
  };

  const renderVerse = () => {
    if (!challenge) return null;
    const parts = challenge.display_text.split('____');
    let blankIndex = 0;
    return (
      <View style={styles.verseContainer} data-testid="verse-challenge-text">
        <Text style={styles.verseTextWrapper}>
          {parts.map((part, i) => (
            <React.Fragment key={i}>
              <Text style={styles.verseWord}>{part}</Text>
              {i < parts.length - 1 && (
                <View style={styles.blankInlineWrap}>
                  {result ? (
                    <View style={[styles.resultBlank, result.results[blankIndex]?.correct ? styles.correctBlank : styles.wrongBlank]}>
                      <Text style={styles.resultBlankText}>
                        {result.results[blankIndex]?.correct
                          ? result.results[blankIndex]?.given
                          : result.results[blankIndex]?.expected}
                      </Text>
                      <Ionicons
                        name={result.results[blankIndex]?.correct ? 'checkmark-circle' : 'close-circle'}
                        size={14}
                        color={result.results[blankIndex]?.correct ? '#4ECDC4' : '#FF6B6B'}
                      />
                    </View>
                  ) : (
                    <TextInput
                      style={styles.blankInput}
                      value={answers[blankIndex] || ''}
                      onChangeText={(v) => updateAnswer(blankIndex, v)}
                      placeholder={`word ${blankIndex + 1}`}
                      placeholderTextColor="#B2BEC3"
                      autoCapitalize="none"
                      autoCorrect={false}
                      data-testid={`blank-input-${blankIndex}`}
                    />
                  )}
                  <Text style={{ display: 'none' }}>{(blankIndex = blankIndex + 1) && ''}</Text>
                </View>
              )}
            </React.Fragment>
          ))}
        </Text>
      </View>
    );
  };

  // Fix: render blanks as separate elements below the verse text for better layout
  const renderChallengeUI = () => {
    if (!challenge) return null;
    const parts = challenge.display_text.split('____');
    return (
      <View>
        {/* Verse with numbered blanks */}
        <View style={styles.verseCard} data-testid="verse-challenge-card">
          <View style={styles.verseHeaderRow}>
            <Ionicons name="book" size={18} color="#6C5CE7" />
            <Text style={styles.verseRef}>{challenge.reference}</Text>
            <View style={[styles.themeBadge, { backgroundColor: `${DIFFICULTIES.find(d => d.value === challenge.difficulty)?.color || '#FFD93D'}20` }]}>
              <Text style={[styles.themeText, { color: DIFFICULTIES.find(d => d.value === challenge.difficulty)?.color || '#FFD93D' }]}>{challenge.theme}</Text>
            </View>
          </View>
          <Text style={styles.verseDisplayText}>
            {parts.map((part, i) => (
              <React.Fragment key={i}>
                <Text>{part}</Text>
                {i < parts.length - 1 && (
                  <Text style={styles.blankMarker}> [{i + 1}] </Text>
                )}
              </React.Fragment>
            ))}
          </Text>
        </View>

        {/* Answer inputs */}
        <View style={styles.answersSection}>
          <Text style={styles.answersSectionTitle}>Fill in the blanks:</Text>
          {Array.from({ length: challenge.blank_count }).map((_, i) => (
            <View key={i} style={styles.answerRow}>
              <View style={styles.answerNumber}>
                <Text style={styles.answerNumberText}>{i + 1}</Text>
              </View>
              {result ? (
                <View style={[styles.resultRow, result.results[i]?.correct ? styles.resultRowCorrect : styles.resultRowWrong]}>
                  <Text style={styles.resultAnswerText}>
                    {result.results[i]?.correct
                      ? result.results[i]?.given
                      : `${result.results[i]?.given || '(empty)'}`}
                  </Text>
                  {!result.results[i]?.correct && (
                    <Text style={styles.expectedText}>{result.results[i]?.expected}</Text>
                  )}
                  <Ionicons
                    name={result.results[i]?.correct ? 'checkmark-circle' : 'close-circle'}
                    size={22}
                    color={result.results[i]?.correct ? '#4ECDC4' : '#FF6B6B'}
                  />
                </View>
              ) : (
                <TextInput
                  style={styles.answerInput}
                  value={answers[i] || ''}
                  onChangeText={(v) => updateAnswer(i, v)}
                  placeholder="Type the missing word..."
                  placeholderTextColor="#B2BEC3"
                  autoCapitalize="none"
                  autoCorrect={false}
                  data-testid={`answer-input-${i}`}
                />
              )}
            </View>
          ))}
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Header */}
      <LinearGradient colors={['#6C5CE7', '#A29BFE']} style={styles.header}>
        <SafeAreaView edges={['top']} style={styles.headerContent}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} data-testid="challenge-back-btn">
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.headerTitle}>Memory Challenge</Text>
            {stats && stats.current_streak > 0 && (
              <View style={styles.streakBadge} data-testid="streak-badge">
                <Ionicons name="flame" size={14} color="#FFD93D" />
                <Text style={styles.streakText}>{stats.current_streak} day streak</Text>
              </View>
            )}
          </View>
          <View style={{ width: 40 }} />
        </SafeAreaView>
      </LinearGradient>

      <ScrollView style={styles.scrollBody} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Animated.View style={{ opacity: fadeAnim, transform: [{ scale: scaleAnim }] }}>

          {/* Stats Bar */}
          {stats && stats.total_played > 0 && (
            <View style={styles.statsBar} data-testid="challenge-stats">
              <View style={styles.statItem}>
                <Text style={styles.statValue}>{stats.total_played}</Text>
                <Text style={styles.statLabel}>Played</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.statItem}>
                <Text style={styles.statValue}>{stats.average_score}%</Text>
                <Text style={styles.statLabel}>Average</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.statItem}>
                <Text style={styles.statValue}>{stats.perfect_scores}</Text>
                <Text style={styles.statLabel}>Perfect</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.statItem}>
                <Text style={[styles.statValue, { color: '#FF6B6B' }]}>{stats.best_streak}</Text>
                <Text style={styles.statLabel}>Best Streak</Text>
              </View>
            </View>
          )}

          {/* Difficulty Selector */}
          {!result && (
            <View style={styles.difficultyRow} data-testid="difficulty-selector">
              {DIFFICULTIES.map((d) => (
                <TouchableOpacity
                  key={d.value}
                  style={[
                    styles.difficultyBtn,
                    (difficulty === d.value || (difficulty === 'auto' && challenge?.difficulty === d.value)) && { backgroundColor: d.color, borderColor: d.color },
                  ]}
                  onPress={() => setDifficulty(d.value)}
                  data-testid={`difficulty-${d.value}`}
                >
                  <Ionicons name={d.icon as any} size={16} color={(difficulty === d.value || (difficulty === 'auto' && challenge?.difficulty === d.value)) ? '#fff' : d.color} />
                  <Text style={[styles.difficultyLabel, (difficulty === d.value || (difficulty === 'auto' && challenge?.difficulty === d.value)) && { color: '#fff' }]}>{d.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          {/* Challenge Content */}
          {loading ? (
            <View style={styles.loadingBox}>
              <ActivityIndicator size="large" color="#6C5CE7" />
              <Text style={styles.loadingText}>Loading today's challenge...</Text>
            </View>
          ) : challenge ? (
            <>
              {renderChallengeUI()}

              {/* Result */}
              {result ? (
                <Animated.View style={[styles.resultCard, { transform: [{ scale: resultAnim }] }]} data-testid="challenge-result">
                  <View style={[styles.scoreCircle, { borderColor: result.score >= 75 ? '#4ECDC4' : result.score >= 50 ? '#FFD93D' : '#FF6B6B' }]}>
                    <Text style={[styles.scoreText, { color: result.score >= 75 ? '#4ECDC4' : result.score >= 50 ? '#FFD93D' : '#FF6B6B' }]}>{result.score}%</Text>
                  </View>
                  <Text style={styles.resultMessage}>{result.message}</Text>
                  <Text style={styles.resultDetail}>{result.correct} of {result.total} correct</Text>
                  {result.streak > 1 && (
                    <View style={styles.streakResultBadge}>
                      <Ionicons name="flame" size={18} color="#FFD93D" />
                      <Text style={styles.streakResultText}>{result.streak} day streak!</Text>
                    </View>
                  )}

                  {/* Full verse reveal */}
                  <View style={styles.fullVerseReveal}>
                    <Text style={styles.fullVerseLabel}>The full verse:</Text>
                    <Text style={styles.fullVerseText}>"{result.full_verse}"</Text>
                    <Text style={styles.fullVerseRef}>— {result.reference}</Text>
                  </View>

                  <View style={styles.resultActions}>
                    <TouchableOpacity style={styles.retryBtn} onPress={handleRetry} data-testid="retry-btn">
                      <Ionicons name="refresh" size={20} color="#6C5CE7" />
                      <Text style={styles.retryText}>Try Again</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.homeBtn} onPress={() => router.back()} data-testid="back-home-btn">
                      <LinearGradient colors={['#6C5CE7', '#A29BFE']} style={styles.homeBtnGradient}>
                        <Ionicons name="home" size={20} color="#fff" />
                        <Text style={styles.homeText}>Home</Text>
                      </LinearGradient>
                    </TouchableOpacity>
                  </View>
                </Animated.View>
              ) : (
                <TouchableOpacity
                  style={[styles.submitBtn, answers.some(a => !a.trim()) && styles.submitBtnDisabled]}
                  onPress={handleSubmit}
                  disabled={submitting || answers.some(a => !a.trim())}
                  data-testid="submit-challenge-btn"
                >
                  <LinearGradient
                    colors={answers.every(a => a.trim()) ? ['#6C5CE7', '#A29BFE'] : ['#DDD', '#CCC']}
                    style={styles.submitGradient}
                  >
                    {submitting ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <>
                        <Ionicons name="checkmark-done" size={24} color="#fff" />
                        <Text style={styles.submitText}>Check My Answers</Text>
                      </>
                    )}
                  </LinearGradient>
                </TouchableOpacity>
              )}
            </>
          ) : (
            <View style={styles.loadingBox}>
              <Text style={styles.loadingText}>Could not load today's challenge</Text>
            </View>
          )}

          <View style={{ height: 40 }} />
        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FF' },
  header: { paddingBottom: 16 },
  headerContent: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: 8 },
  backBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center' },
  headerCenter: { alignItems: 'center' },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#fff' },
  streakBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 10, paddingVertical: 3, borderRadius: 12, marginTop: 4, gap: 4 },
  streakText: { fontSize: 12, color: '#FFD93D', fontWeight: '700' },
  scrollBody: { flex: 1 },
  scrollContent: { padding: 20 },

  // Stats
  statsBar: { flexDirection: 'row', backgroundColor: '#fff', borderRadius: 20, padding: 16, marginBottom: 16, alignItems: 'center', justifyContent: 'space-around', shadowColor: '#6C5CE7', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 12, elevation: 4 },
  statItem: { alignItems: 'center' },
  statValue: { fontSize: 22, fontWeight: '800', color: '#6C5CE7' },
  statLabel: { fontSize: 11, color: '#636E72', fontWeight: '600', marginTop: 2 },
  statDivider: { width: 1, height: 30, backgroundColor: '#E0E0E0' },

  // Difficulty
  difficultyRow: { flexDirection: 'row', justifyContent: 'center', gap: 10, marginBottom: 20 },
  difficultyBtn: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 20, borderWidth: 2, borderColor: '#E0E0E0', backgroundColor: '#fff', gap: 6 },
  difficultyLabel: { fontSize: 14, fontWeight: '700', color: '#636E72' },

  // Verse Card
  verseCard: { backgroundColor: '#fff', borderRadius: 24, padding: 20, marginBottom: 16, shadowColor: '#6C5CE7', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 12, elevation: 4 },
  verseHeaderRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 14, gap: 8 },
  verseRef: { fontSize: 15, fontWeight: '700', color: '#6C5CE7', flex: 1 },
  themeBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10 },
  themeText: { fontSize: 11, fontWeight: '700', textTransform: 'capitalize' },
  verseDisplayText: { fontSize: 18, lineHeight: 30, color: '#2D3436', fontWeight: '500' },
  blankMarker: { fontSize: 18, fontWeight: '800', color: '#6C5CE7', backgroundColor: '#EDE9FE', borderRadius: 6, overflow: 'hidden' },

  // Answers Section
  answersSection: { marginBottom: 20 },
  answersSectionTitle: { fontSize: 16, fontWeight: '700', color: '#2D3436', marginBottom: 12 },
  answerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 10, gap: 10 },
  answerNumber: { width: 32, height: 32, borderRadius: 16, backgroundColor: '#6C5CE7', alignItems: 'center', justifyContent: 'center' },
  answerNumberText: { color: '#fff', fontWeight: '800', fontSize: 14 },
  answerInput: { flex: 1, backgroundColor: '#fff', borderRadius: 16, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, color: '#2D3436', borderWidth: 2, borderColor: '#E0E0E0', fontWeight: '500' },

  // Result Row
  resultRow: { flex: 1, flexDirection: 'row', alignItems: 'center', borderRadius: 16, paddingHorizontal: 16, paddingVertical: 14, gap: 8, borderWidth: 2 },
  resultRowCorrect: { backgroundColor: '#E0F7F5', borderColor: '#4ECDC4' },
  resultRowWrong: { backgroundColor: '#FFE8E8', borderColor: '#FF6B6B' },
  resultAnswerText: { flex: 1, fontSize: 16, fontWeight: '600', color: '#2D3436' },
  expectedText: { fontSize: 13, fontWeight: '700', color: '#4ECDC4' },

  // Submit
  submitBtn: { borderRadius: 20, overflow: 'hidden', shadowColor: '#6C5CE7', shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 6 },
  submitBtnDisabled: { opacity: 0.6 },
  submitGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 18, gap: 10 },
  submitText: { color: '#fff', fontSize: 18, fontWeight: '700' },

  // Result Card
  resultCard: { backgroundColor: '#fff', borderRadius: 24, padding: 24, alignItems: 'center', marginTop: 20, shadowColor: '#6C5CE7', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.15, shadowRadius: 20, elevation: 8 },
  scoreCircle: { width: 100, height: 100, borderRadius: 50, borderWidth: 6, alignItems: 'center', justifyContent: 'center', marginBottom: 16 },
  scoreText: { fontSize: 32, fontWeight: '900' },
  resultMessage: { fontSize: 18, fontWeight: '700', color: '#2D3436', textAlign: 'center', marginBottom: 6 },
  resultDetail: { fontSize: 14, color: '#636E72', marginBottom: 12 },
  streakResultBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFF8E0', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, gap: 6, marginBottom: 16 },
  streakResultText: { fontSize: 14, fontWeight: '700', color: '#FF6B6B' },
  fullVerseReveal: { backgroundColor: '#F8F9FF', borderRadius: 16, padding: 16, width: '100%', marginBottom: 20 },
  fullVerseLabel: { fontSize: 12, fontWeight: '700', color: '#6C5CE7', marginBottom: 8 },
  fullVerseText: { fontSize: 15, fontStyle: 'italic', color: '#2D3436', lineHeight: 24 },
  fullVerseRef: { fontSize: 13, fontWeight: '700', color: '#6C5CE7', marginTop: 8 },
  resultActions: { flexDirection: 'row', gap: 12, width: '100%' },
  retryBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 14, borderRadius: 16, borderWidth: 2, borderColor: '#6C5CE7', gap: 8 },
  retryText: { fontSize: 15, fontWeight: '700', color: '#6C5CE7' },
  homeBtn: { flex: 1, borderRadius: 16, overflow: 'hidden' },
  homeBtnGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 14, gap: 8 },
  homeText: { fontSize: 15, fontWeight: '700', color: '#fff' },

  // Loading
  loadingBox: { alignItems: 'center', padding: 40 },
  loadingText: { fontSize: 15, color: '#636E72', marginTop: 12 },

  // Inline blanks (unused but kept for reference)
  verseContainer: { marginBottom: 20 },
  verseTextWrapper: { fontSize: 18, lineHeight: 32, color: '#2D3436' },
  verseWord: { fontSize: 18, color: '#2D3436' },
  blankInlineWrap: { },
  blankInput: { borderBottomWidth: 2, borderBottomColor: '#6C5CE7', minWidth: 80, fontSize: 16, paddingVertical: 2, color: '#6C5CE7', fontWeight: '600', textAlign: 'center' },
  resultBlank: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  correctBlank: { backgroundColor: '#E0F7F5' },
  wrongBlank: { backgroundColor: '#FFE8E8' },
  resultBlankText: { fontSize: 16, fontWeight: '700' },
});
