import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Animated,
  StatusBar,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuthContext } from '../contexts/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Story {
  week_key: string;
  week_number: number;
  title: string;
  reference: string;
  characters: string[];
  theme: string;
  icon: string;
  colors: string[];
  summary: string;
  narrative: string;
  discussion_questions: string[];
  age_tier: string;
}

interface Badge {
  id: string;
  name: string;
  icon: string;
  color: string;
  description: string;
}

export default function BibleStoryScreen() {
  const { activeChild } = useAuthContext();
  const [story, setStory] = useState<Story | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDiscussion, setShowDiscussion] = useState(false);
  const [isRead, setIsRead] = useState(false);
  const [marking, setMarking] = useState(false);
  const [newBadges, setNewBadges] = useState<Badge[]>([]);
  const [showBadgeModal, setShowBadgeModal] = useState(false);
  const [streakInfo, setStreakInfo] = useState({ current_streak: 0, total_read: 0 });
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const discussionAnim = useRef(new Animated.Value(0)).current;
  const checkAnim = useRef(new Animated.Value(0)).current;

  const ageTier = activeChild?.age_tier || '7-9';
  const childId = activeChild?.child_id;

  useEffect(() => {
    fetchStory();
    if (childId) fetchReadStatus();
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
  }, []);

  const fetchStory = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/story-of-the-week?age_tier=${ageTier}`);
      if (res.ok) setStory(await res.json());
    } catch (e) {
      console.log('Story fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchReadStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/story-progress/${childId}`);
      if (res.ok) {
        const data = await res.json();
        setStreakInfo({ current_streak: data.current_streak, total_read: data.total_read });
        // Check if current week's story is already read
        const currentWeekKey = story?.week_key;
        if (data.read_week_keys && currentWeekKey) {
          setIsRead(data.read_week_keys.includes(currentWeekKey));
        }
      }
    } catch (e) {
      console.log('Progress fetch error:', e);
    }
  };

  // Re-check read status once story loads
  useEffect(() => {
    if (story && childId) {
      (async () => {
        try {
          const res = await fetch(`${BACKEND_URL}/api/story-progress/${childId}`);
          if (res.ok) {
            const data = await res.json();
            setStreakInfo({ current_streak: data.current_streak, total_read: data.total_read });
            if (data.read_week_keys?.includes(story.week_key)) setIsRead(true);
          }
        } catch (e) {}
      })();
    }
  }, [story?.week_key, childId]);

  const handleMarkRead = async () => {
    if (!story || !childId || isRead || marking) return;
    setMarking(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/story-progress/mark-read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          child_id: childId,
          week_key: story.week_key,
          story_title: story.title,
          story_reference: story.reference,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setIsRead(true);
        setStreakInfo({ current_streak: data.current_streak, total_read: data.total_read });
        Animated.spring(checkAnim, { toValue: 1, tension: 50, friction: 5, useNativeDriver: true }).start();
        if (data.new_badges && data.new_badges.length > 0) {
          setNewBadges(data.new_badges);
          setTimeout(() => setShowBadgeModal(true), 600);
        }
      }
    } catch (e) {
      console.log('Mark read error:', e);
    } finally {
      setMarking(false);
    }
  };

  const toggleDiscussion = () => {
    const newVal = !showDiscussion;
    setShowDiscussion(newVal);
    Animated.spring(discussionAnim, { toValue: newVal ? 1 : 0, tension: 50, friction: 7, useNativeDriver: true }).start();
  };

  const renderNarrative = (text: string) => {
    const paragraphs = text.split('\n\n').filter(p => p.trim());
    return paragraphs.map((p, i) => (
      <Text key={i} style={styles.paragraph}>{p.trim()}</Text>
    ));
  };

  if (loading) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color="#6C5CE7" />
        <Text style={{ marginTop: 16, fontSize: 16, color: '#636E72' }}>Loading this week's story...</Text>
      </View>
    );
  }

  if (!story) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center', padding: 40 }]}>
        <Ionicons name="book-outline" size={64} color="#DDD" />
        <Text style={{ fontSize: 18, fontWeight: '700', color: '#2D3436', marginTop: 16 }}>Story unavailable</Text>
        <TouchableOpacity onPress={() => router.back()} style={{ marginTop: 20 }}>
          <Text style={{ color: '#6C5CE7', fontWeight: '600' }}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const [color1, color2] = story.colors || ['#6C5CE7', '#A29BFE'];

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <ScrollView style={{ flex: 1 }} showsVerticalScrollIndicator={false}>
        <Animated.View style={{ opacity: fadeAnim }}>
          {/* Hero Header */}
          <LinearGradient colors={[color1, color2]} style={styles.hero}>
            <SafeAreaView edges={['top']} style={styles.heroTop}>
              <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} data-testid="story-back-btn">
                <Ionicons name="arrow-back" size={24} color="#fff" />
              </TouchableOpacity>
              <View style={styles.weekBadge}>
                <Text style={styles.weekText}>Week {story.week_number}</Text>
              </View>
              <View style={{ width: 40 }} />
            </SafeAreaView>

            <View style={styles.heroContent}>
              <View style={styles.iconCircle}>
                <Ionicons name={story.icon as any} size={48} color="#fff" />
              </View>
              <Text style={styles.heroTitle} data-testid="story-title">{story.title}</Text>
              <Text style={styles.heroRef}>{story.reference}</Text>
              <View style={styles.themePill}>
                <Text style={styles.themeText}>{story.theme}</Text>
              </View>
            </View>

            {/* Characters */}
            <View style={styles.charactersRow}>
              {story.characters.map((char, i) => (
                <View key={i} style={styles.characterPill}>
                  <Ionicons name="person" size={12} color="#fff" />
                  <Text style={styles.characterText}>{char}</Text>
                </View>
              ))}
            </View>
          </LinearGradient>

          {/* Reading Progress Strip */}
          {childId && (
            <View style={styles.progressStrip} data-testid="progress-strip">
              <View style={styles.progressItem}>
                <Ionicons name="flame" size={18} color="#FF6B6B" />
                <Text style={styles.progressValue}>{streakInfo.current_streak}</Text>
                <Text style={styles.progressLabel}>Streak</Text>
              </View>
              <View style={styles.progressDivider} />
              <View style={styles.progressItem}>
                <Ionicons name="book" size={18} color="#6C5CE7" />
                <Text style={styles.progressValue}>{streakInfo.total_read}</Text>
                <Text style={styles.progressLabel}>Read</Text>
              </View>
              <View style={styles.progressDivider} />
              <View style={styles.progressItem}>
                <Ionicons name="library" size={18} color="#4ECDC4" />
                <Text style={styles.progressValue}>52</Text>
                <Text style={styles.progressLabel}>Total</Text>
              </View>
            </View>
          )}

          {/* Narrative */}
          <View style={styles.narrativeSection} data-testid="story-narrative">
            <View style={styles.sectionHeader}>
              <Ionicons name="book" size={20} color="#6C5CE7" />
              <Text style={styles.sectionTitle}>The Story</Text>
            </View>
            {renderNarrative(story.narrative)}
          </View>

          {/* Mark as Read Button */}
          {childId && (
            <View style={styles.markReadSection} data-testid="mark-read-section">
              <TouchableOpacity
                style={[styles.markReadBtn, isRead && styles.markReadBtnDone]}
                onPress={handleMarkRead}
                disabled={isRead || marking}
                activeOpacity={0.8}
                data-testid="mark-read-btn"
              >
                {marking ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <>
                    <Animated.View style={{ transform: [{ scale: isRead ? checkAnim.interpolate({ inputRange: [0, 1], outputRange: [0.5, 1] }) : 1 }] }}>
                      <Ionicons name={isRead ? 'checkmark-circle' : 'checkmark-circle-outline'} size={24} color="#fff" />
                    </Animated.View>
                    <Text style={styles.markReadText}>
                      {isRead ? "Story Complete!" : "Mark as Read"}
                    </Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          )}

          {/* Discussion Questions */}
          <View style={styles.discussionSection} data-testid="discussion-questions">
            <TouchableOpacity style={styles.discussionToggle} onPress={toggleDiscussion} activeOpacity={0.8} data-testid="toggle-discussion">
              <View style={styles.discussionHeader}>
                <Ionicons name="chatbubbles" size={22} color="#FF6B6B" />
                <Text style={styles.discussionTitle}>Family Discussion</Text>
              </View>
              <Ionicons name={showDiscussion ? 'chevron-up' : 'chevron-down'} size={22} color="#FF6B6B" />
            </TouchableOpacity>

            {showDiscussion && (
              <Animated.View style={{ opacity: discussionAnim }}>
                {story.discussion_questions.map((q, i) => (
                  <View key={i} style={styles.questionCard}>
                    <View style={[styles.questionNum, { backgroundColor: `${color1}20` }]}>
                      <Text style={[styles.questionNumText, { color: color1 }]}>{i + 1}</Text>
                    </View>
                    <Text style={styles.questionText}>{q}</Text>
                  </View>
                ))}
              </Animated.View>
            )}
          </View>

          {/* Bottom Actions */}
          <View style={styles.bottomActions}>
            <TouchableOpacity style={styles.actionBtn} onPress={() => router.push('/chat')} data-testid="discuss-with-buddy-btn">
              <LinearGradient colors={[color1, color2]} style={styles.actionBtnGradient}>
                <Ionicons name="chatbubble-ellipses" size={22} color="#fff" />
                <Text style={styles.actionBtnText}>Discuss with Bible Buddy</Text>
              </LinearGradient>
            </TouchableOpacity>
          </View>

          <View style={{ height: 40 }} />
        </Animated.View>
      </ScrollView>

      {/* New Badge Modal */}
      <Modal visible={showBadgeModal} transparent animationType="fade" data-testid="badge-modal">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalStars}>
              <Ionicons name="star" size={28} color="#FFD93D" />
              <Ionicons name="star" size={36} color="#FFD93D" />
              <Ionicons name="star" size={28} color="#FFD93D" />
            </View>
            <Text style={styles.modalTitle}>Badge Earned!</Text>
            {newBadges.map((badge, i) => (
              <View key={i} style={styles.badgeModalItem}>
                <View style={[styles.badgeCircle, { backgroundColor: `${badge.color}20` }]}>
                  <Ionicons name={badge.icon as any} size={32} color={badge.color} />
                </View>
                <Text style={styles.badgeName}>{badge.name}</Text>
                <Text style={styles.badgeDesc}>{badge.description}</Text>
              </View>
            ))}
            <TouchableOpacity
              style={styles.modalCloseBtn}
              onPress={() => setShowBadgeModal(false)}
              data-testid="close-badge-modal"
            >
              <Text style={styles.modalCloseText}>Awesome!</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FF' },

  // Hero
  hero: { paddingBottom: 30 },
  heroTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: 8 },
  backBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center' },
  weekBadge: { backgroundColor: 'rgba(255,255,255,0.25)', paddingHorizontal: 14, paddingVertical: 5, borderRadius: 12 },
  weekText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  heroContent: { alignItems: 'center', paddingHorizontal: 24, paddingTop: 16 },
  iconCircle: { width: 90, height: 90, borderRadius: 45, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center', marginBottom: 16 },
  heroTitle: { fontSize: 26, fontWeight: '900', color: '#fff', textAlign: 'center', lineHeight: 32 },
  heroRef: { fontSize: 15, color: 'rgba(255,255,255,0.8)', marginTop: 6, fontWeight: '600' },
  themePill: { backgroundColor: 'rgba(255,255,255,0.25)', paddingHorizontal: 16, paddingVertical: 6, borderRadius: 16, marginTop: 12 },
  themeText: { color: '#fff', fontWeight: '700', fontSize: 13 },
  charactersRow: { flexDirection: 'row', justifyContent: 'center', flexWrap: 'wrap', gap: 8, paddingHorizontal: 20, marginTop: 16 },
  characterPill: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, gap: 4 },
  characterText: { color: '#fff', fontSize: 12, fontWeight: '600' },

  // Progress Strip
  progressStrip: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around', backgroundColor: '#fff', marginHorizontal: 20, marginTop: -16, borderRadius: 16, paddingVertical: 14, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.08, shadowRadius: 12, elevation: 4 },
  progressItem: { alignItems: 'center', gap: 2 },
  progressValue: { fontSize: 20, fontWeight: '800', color: '#2D3436' },
  progressLabel: { fontSize: 11, color: '#636E72', fontWeight: '600' },
  progressDivider: { width: 1, height: 36, backgroundColor: '#F0F0F0' },

  // Narrative
  narrativeSection: { padding: 24 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 20 },
  sectionTitle: { fontSize: 20, fontWeight: '800', color: '#2D3436' },
  paragraph: { fontSize: 17, lineHeight: 28, color: '#2D3436', marginBottom: 18 },

  // Mark as Read
  markReadSection: { paddingHorizontal: 20, marginBottom: 20 },
  markReadBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#6C5CE7', paddingVertical: 16, borderRadius: 20, gap: 10, shadowColor: '#6C5CE7', shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 6 },
  markReadBtnDone: { backgroundColor: '#4ECDC4' },
  markReadText: { color: '#fff', fontSize: 17, fontWeight: '700' },

  // Discussion
  discussionSection: { marginHorizontal: 20, backgroundColor: '#fff', borderRadius: 24, padding: 20, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.08, shadowRadius: 12, elevation: 4, marginBottom: 20 },
  discussionToggle: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  discussionHeader: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  discussionTitle: { fontSize: 18, fontWeight: '700', color: '#2D3436' },
  questionCard: { flexDirection: 'row', alignItems: 'flex-start', marginTop: 16, gap: 12 },
  questionNum: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  questionNumText: { fontWeight: '800', fontSize: 15 },
  questionText: { flex: 1, fontSize: 15, lineHeight: 22, color: '#2D3436' },

  // Bottom
  bottomActions: { paddingHorizontal: 20 },
  actionBtn: { borderRadius: 20, overflow: 'hidden', shadowColor: '#6C5CE7', shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 6 },
  actionBtnGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 18, gap: 10 },
  actionBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },

  // Badge Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', alignItems: 'center', padding: 30 },
  modalContent: { backgroundColor: '#fff', borderRadius: 28, padding: 30, alignItems: 'center', width: '100%', maxWidth: 340 },
  modalStars: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  modalTitle: { fontSize: 24, fontWeight: '800', color: '#2D3436', marginBottom: 20 },
  badgeModalItem: { alignItems: 'center', marginBottom: 16 },
  badgeCircle: { width: 72, height: 72, borderRadius: 36, alignItems: 'center', justifyContent: 'center', marginBottom: 10 },
  badgeName: { fontSize: 18, fontWeight: '700', color: '#2D3436' },
  badgeDesc: { fontSize: 14, color: '#636E72', marginTop: 4, textAlign: 'center' },
  modalCloseBtn: { backgroundColor: '#6C5CE7', paddingHorizontal: 40, paddingVertical: 14, borderRadius: 20, marginTop: 10 },
  modalCloseText: { color: '#fff', fontSize: 17, fontWeight: '700' },
});
