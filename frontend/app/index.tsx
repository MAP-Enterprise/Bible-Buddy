import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  StatusBar,
  ScrollView,
  Platform,
  Share,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { storage } from '../helpers/storage';
import { useAuthContext } from '../contexts/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface VerseOfTheDay {
  date: string;
  verse: string;
  reference: string;
  theme: string;
  explanation: string;
}

interface WeeklyStory {
  title: string;
  reference: string;
  theme: string;
  icon: string;
  colors: string[];
  summary: string;
  week_number: number;
}

export default function HomeScreen() {
  const { isAuthenticated, isLoading: authLoading, user, children: childProfiles, activeChild, logout } = useAuthContext();
  const bounceAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const [verseData, setVerseData] = useState<VerseOfTheDay | null>(null);
  const [verseLoading, setVerseLoading] = useState(true);
  const [storyData, setStoryData] = useState<WeeklyStory | null>(null);
  const [storyProgress, setStoryProgress] = useState<{ current_streak: number; total_read: number; badges_earned: number } | null>(null);
  const [copied, setCopied] = useState(false);
  const [readingNightTonight, setReadingNightTonight] = useState(false);
  const [storyPreview, setStoryPreview] = useState<{ title: string; theme: string } | null>(null);

  useEffect(() => {
    Animated.parallel([
      Animated.spring(scaleAnim, { toValue: 1, tension: 50, friction: 7, useNativeDriver: true }),
      Animated.timing(fadeAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
    ]).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(bounceAnim, { toValue: -12, duration: 1200, useNativeDriver: true }),
        Animated.timing(bounceAnim, { toValue: 0, duration: 1200, useNativeDriver: true }),
      ])
    ).start();

    fetchVerseOfTheDay();
    fetchStoryPreview();
    checkReadingNight();
  }, []);

  const fetchStoryPreview = async () => {
    try {
      const ageTier = activeChild?.age_tier || '7-9';
      const res = await fetch(`${BACKEND_URL}/api/story-of-the-week?age_tier=${ageTier}`);
      if (res.ok) {
        const data = await res.json();
        setStoryData(data);
      }
    } catch (e) {
      console.log('Story fetch error:', e);
    }
    // Fetch progress if child is active
    if (activeChild?.child_id) {
      try {
        const res = await fetch(`${BACKEND_URL}/api/story-progress/${activeChild.child_id}`);
        if (res.ok) {
          const data = await res.json();
          setStoryProgress({ current_streak: data.current_streak, total_read: data.total_read, badges_earned: data.badges_earned });
        }
      } catch (e) {
        console.log('Progress fetch error:', e);
      }
    }
  };

  const checkReadingNight = async () => {
    try {
      // Fetch preview regardless (it's public)
      const previewRes = await fetch(`${BACKEND_URL}/api/notifications/reading-night-preview`);
      if (previewRes.ok) {
        const preview = await previewRes.json();
        setStoryPreview({ title: preview.title, theme: preview.theme });
      }
      // Only check reading night settings if authenticated
      if (!isAuthenticated) return;
      const token = await storage.getItem('token');
      if (!token) return;
      const res = await fetch(`${BACKEND_URL}/api/notifications/reading-night`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const settings = await res.json();
        if (settings.enabled) {
          const days = ['sunday','monday','tuesday','wednesday','thursday','friday','saturday'];
          const today = days[new Date().getUTCDay()];
          if (today === settings.day) setReadingNightTonight(true);
        }
      }
    } catch (e) {
      console.log('Reading night check error:', e);
    }
  };


  const fetchVerseOfTheDay = async () => {
    try {
      const ageTier = activeChild?.age_tier || (await storage.getItem('ageTier')) || '7-9';
      const res = await fetch(`${BACKEND_URL}/api/verse-of-the-day?age_tier=${ageTier}`);
      if (res.ok) {
        const data = await res.json();
        setVerseData(data);
      }
    } catch (e) {
      console.log('Verse fetch error:', e);
    } finally {
      setVerseLoading(false);
    }
  };

  const handleShareVerse = async () => {
    if (!verseData) return;
    const shareText = `"${verseData.verse}"\n— ${verseData.reference}\n\nShared from Bible Buddy`;
    if (Platform.OS === 'web') {
      try {
        await navigator.clipboard.writeText(shareText);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } else {
      Share.share({ message: shareText });
    }
  };

  if (authLoading) {
    return (
      <View style={[styles.container, { alignItems: 'center', justifyContent: 'center' }]}>
        <ActivityIndicator size="large" color="#667eea" />
      </View>
    );
  }

  const features = [
    { icon: 'chatbubbles', color: '#FF6B6B', bg: '#FFE8E8', label: 'Chat', route: '/chat' },
    { icon: 'mic', color: '#4ECDC4', bg: '#E0F7F5', label: 'Voice', route: '/chat' },
    { icon: 'book', color: '#FFD93D', bg: '#FFF8E0', label: 'Learn', route: '/bible-story' },
    { icon: 'shield-checkmark', color: '#6C5CE7', bg: '#EDE9FE', label: 'Safe', route: '/parent-dashboard' },
  ];

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <LinearGradient
        colors={['#667eea', '#764ba2']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.headerGradient}
      >
        <SafeAreaView edges={['top']}>
          <Animated.View style={[styles.logoContainer, { transform: [{ translateY: bounceAnim }, { scale: scaleAnim }], opacity: fadeAnim }]}>
            <View style={styles.logoCircle}>
              <Text style={styles.logoEmoji}>{'\ud83d\udcd6'}</Text>
            </View>
            <Text style={styles.logoText}>Bible Buddy</Text>
            {isAuthenticated && user ? (
              <Text style={styles.tagline}>Welcome, {user.name}!</Text>
            ) : (
              <Text style={styles.tagline}>Your Friendly Faith Companion!</Text>
            )}
          </Animated.View>
        </SafeAreaView>
      </LinearGradient>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
        <Animated.View style={{ opacity: fadeAnim }}>
          {/* Welcome Card */}
          <View style={styles.welcomeCard} data-testid="welcome-card">
            {isAuthenticated && activeChild ? (
              <>
                <Text style={styles.welcomeTitle} data-testid="welcome-child-name">
                  {activeChild.name}'s Bible Buddy
                </Text>
                <Text style={styles.welcomeText}>
                  Age group: {activeChild.age_tier} years | Ready to explore God's word!
                </Text>
              </>
            ) : (
              <>
                <Text style={styles.welcomeTitle}>Hey there, friend!</Text>
                <Text style={styles.welcomeText}>
                  I'm here to help you learn about God, Jesus, and the Bible in a fun way!
                </Text>
              </>
            )}
          </View>

          {/* Reading Night Tonight Banner */}
          {readingNightTonight && storyPreview && (
            <TouchableOpacity
              style={styles.readingNightBanner}
              onPress={() => router.push('/bible-story')}
              activeOpacity={0.8}
              data-testid="reading-night-banner"
            >
              <LinearGradient
                colors={['#FF8E53', '#FF6B6B']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.readingNightGradient}
              >
                <Ionicons name="moon" size={22} color="#fff" />
                <View style={{ flex: 1 }}>
                  <Text style={styles.readingNightBannerTitle}>Family Reading Night!</Text>
                  <Text style={styles.readingNightBannerText}>Tonight's story: {storyPreview.title}</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color="rgba(255,255,255,0.7)" />
              </LinearGradient>
            </TouchableOpacity>
          )}

          {/* Verse of the Day */}
          {verseLoading ? (
            <View style={styles.verseCard} data-testid="verse-loading">
              <ActivityIndicator size="small" color="#FFD93D" />
            </View>
          ) : verseData ? (
            <View style={styles.verseCard} data-testid="verse-of-the-day">
              <LinearGradient
                colors={['#1a1a2e', '#16213e', '#0f3460']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.verseGradient}
              >
                <View style={styles.verseHeader}>
                  <View style={styles.verseSunrise}>
                    <Ionicons name="sunny" size={18} color="#FFD93D" />
                  </View>
                  <Text style={styles.verseLabel}>Verse of the Day</Text>
                  <View style={styles.verseThemeBadge}>
                    <Text style={styles.verseThemeText}>{verseData.theme}</Text>
                  </View>
                </View>
                <Text style={styles.verseText}>"{verseData.verse}"</Text>
                <Text style={styles.verseReference}>— {verseData.reference}</Text>
                <View style={styles.verseDivider} />
                <Text style={styles.verseExplanation}>{verseData.explanation}</Text>
                <TouchableOpacity style={styles.verseShareButton} onPress={handleShareVerse} activeOpacity={0.7} data-testid="share-verse-btn">
                  <Ionicons name={copied ? "checkmark-circle" : "share-social"} size={18} color="#FFD93D" />
                  <Text style={styles.verseShareText}>{copied ? 'Copied!' : 'Share Verse'}</Text>
                </TouchableOpacity>
              </LinearGradient>
            </View>
          ) : null}

          {/* Story of the Week */}
          {storyData && (
            <TouchableOpacity
              style={styles.storyCard}
              onPress={() => router.push('/bible-story')}
              activeOpacity={0.9}
              data-testid="story-of-the-week-card"
            >
              <LinearGradient
                colors={storyData.colors || ['#6C5CE7', '#A29BFE']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.storyGradient}
              >
                <View style={styles.storyHeader}>
                  <View style={styles.storyIconCircle}>
                    <Ionicons name={(storyData.icon || 'book') as any} size={24} color="#fff" />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.storyLabel}>Story of the Week</Text>
                    <Text style={styles.storyWeek}>Week {storyData.week_number}</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={22} color="rgba(255,255,255,0.7)" />
                </View>
                <Text style={styles.storyTitle}>{storyData.title}</Text>
                <Text style={styles.storyRef}>{storyData.reference}</Text>
                <Text style={styles.storySummary} numberOfLines={2}>{storyData.summary}</Text>
                <View style={styles.storyFooter}>
                  <View style={styles.storyThemePill}>
                    <Ionicons name="sparkles" size={12} color="#fff" />
                    <Text style={styles.storyThemeText}>{storyData.theme}</Text>
                  </View>
                  {storyProgress && (storyProgress.current_streak > 0 || storyProgress.badges_earned > 0) && (
                    <View style={styles.storyProgressRow} data-testid="story-progress-badges">
                      {storyProgress.current_streak > 0 && (
                        <View style={styles.storyProgressPill}>
                          <Ionicons name="flame" size={12} color="#FFD93D" />
                          <Text style={styles.storyProgressText}>{storyProgress.current_streak}w</Text>
                        </View>
                      )}
                      {storyProgress.badges_earned > 0 && (
                        <View style={styles.storyProgressPill}>
                          <Ionicons name="star" size={12} color="#FFD93D" />
                          <Text style={styles.storyProgressText}>{storyProgress.badges_earned}</Text>
                        </View>
                      )}
                    </View>
                  )}
                </View>
              </LinearGradient>
            </TouchableOpacity>
          )}

          {/* Features Grid */}
          <View style={styles.featuresGrid}>
            <TouchableOpacity
              style={[styles.featureCard, { backgroundColor: '#FFE8E8' }]}
              onPress={() => Alert.alert('Chat', 'Opening Chat...', [{ text: 'Go', onPress: () => router.push('/chat') }, { text: 'Cancel' }])}
              activeOpacity={0.6}
            >
              <View style={[styles.featureIcon, { backgroundColor: '#FF6B6B' }]} pointerEvents="none">
                <Ionicons name="chatbubbles" size={24} color="#fff" />
              </View>
              <Text style={styles.featureLabelChat} pointerEvents="none">Chat</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.featureCard, { backgroundColor: '#E0F7F5' }]}
              onPress={() => Alert.alert('Voice', 'Opening Voice Chat...', [{ text: 'Go', onPress: () => router.push('/chat') }, { text: 'Cancel' }])}
              activeOpacity={0.6}
            >
              <View style={[styles.featureIcon, { backgroundColor: '#4ECDC4' }]} pointerEvents="none">
                <Ionicons name="mic" size={24} color="#fff" />
              </View>
              <Text style={styles.featureLabelVoice} pointerEvents="none">Voice</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.featureCard, { backgroundColor: '#FFF8E0' }]}
              onPress={() => Alert.alert('Learn', 'Opening Bible Story...', [{ text: 'Go', onPress: () => router.push('/bible-story') }, { text: 'Cancel' }])}
              activeOpacity={0.6}
            >
              <View style={[styles.featureIcon, { backgroundColor: '#FFD93D' }]} pointerEvents="none">
                <Ionicons name="book" size={24} color="#fff" />
              </View>
              <Text style={styles.featureLabelLearn} pointerEvents="none">Learn</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.featureCard, { backgroundColor: '#EDE9FE' }]}
              onPress={() => Alert.alert('Safe', 'Opening Parent Dashboard...', [{ text: 'Go', onPress: () => router.push('/parent-dashboard') }, { text: 'Cancel' }])}
              activeOpacity={0.6}
            >
              <View style={[styles.featureIcon, { backgroundColor: '#6C5CE7' }]} pointerEvents="none">
                <Ionicons name="shield-checkmark" size={24} color="#fff" />
              </View>
              <Text style={styles.featureLabelSafe} pointerEvents="none">Safe</Text>
            </TouchableOpacity>
          </View>

          {/* Auth-dependent CTAs */}
          {isAuthenticated ? (
            <>
              {/* Start Chatting */}
              <TouchableOpacity style={styles.primaryButton} onPress={() => router.push('/chat')} activeOpacity={0.9} data-testid="start-chat-btn">
                <LinearGradient colors={['#FF6B6B', '#FF8E53']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.buttonGradient}>
                  <Ionicons name="chatbubble-ellipses" size={28} color="#fff" />
                  <Text style={styles.primaryButtonText}>Start Chatting!</Text>
                  <Ionicons name="arrow-forward-circle" size={28} color="#fff" />
                </LinearGradient>
              </TouchableOpacity>

              {/* Memory Challenge */}
              <TouchableOpacity style={styles.secondaryButton} onPress={() => router.push('/verse-challenge')} activeOpacity={0.9} data-testid="verse-challenge-btn">
                <LinearGradient colors={['#6C5CE7', '#A29BFE']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.buttonGradient}>
                  <Ionicons name="trophy" size={24} color="#fff" />
                  <Text style={styles.secondaryButtonText}>Memory Challenge</Text>
                  <Ionicons name="arrow-forward-circle" size={24} color="#fff" />
                </LinearGradient>
              </TouchableOpacity>

              {/* Add Child / Manage Profiles */}
              {childProfiles.length === 0 ? (
                <TouchableOpacity style={styles.secondaryButton} onPress={() => router.push('/onboarding')} activeOpacity={0.8} data-testid="add-child-btn">
                  <LinearGradient colors={['#4ECDC4', '#44A08D']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.buttonGradient}>
                    <Ionicons name="person-add" size={24} color="#fff" />
                    <Text style={styles.secondaryButtonText}>Add Your Child</Text>
                  </LinearGradient>
                </TouchableOpacity>
              ) : (
                <TouchableOpacity style={styles.secondaryButton} onPress={() => router.push('/onboarding')} activeOpacity={0.8} data-testid="add-another-child-btn">
                  <LinearGradient colors={['#4ECDC4', '#44A08D']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.buttonGradient}>
                    <Ionicons name="person-add" size={24} color="#fff" />
                    <Text style={styles.secondaryButtonText}>Add Another Child</Text>
                  </LinearGradient>
                </TouchableOpacity>
              )}

              {/* Parent Dashboard */}
              <TouchableOpacity style={styles.dashboardButton} onPress={() => router.push('/parent-dashboard')} activeOpacity={0.8} data-testid="parent-dashboard-btn">
                <Ionicons name="people" size={22} color="#6C5CE7" />
                <Text style={styles.dashboardButtonText}>Parent Dashboard</Text>
                <Ionicons name="chevron-forward" size={20} color="#6C5CE7" />
              </TouchableOpacity>

              {/* Logout */}
              <TouchableOpacity
                style={styles.logoutButton}
                onPress={async () => { await logout(); router.replace('/sign-in'); }}
                activeOpacity={0.8}
                data-testid="logout-btn"
              >
                <Ionicons name="log-out-outline" size={20} color="#FF6B6B" />
                <Text style={styles.logoutText}>Sign Out</Text>
              </TouchableOpacity>
            </>
          ) : (
            <>
              {/* Not logged in — CTAs to sign in / sign up */}
              <TouchableOpacity style={styles.primaryButton} onPress={() => router.push('/sign-in')} activeOpacity={0.9} data-testid="sign-in-cta-btn">
                <LinearGradient colors={['#FF6B6B', '#FF8E53']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.buttonGradient}>
                  <Ionicons name="log-in" size={28} color="#fff" />
                  <Text style={styles.primaryButtonText}>Sign In</Text>
                  <Ionicons name="arrow-forward-circle" size={28} color="#fff" />
                </LinearGradient>
              </TouchableOpacity>

              <TouchableOpacity style={styles.secondaryButton} onPress={() => router.push('/sign-up')} activeOpacity={0.8} data-testid="sign-up-cta-btn">
                <LinearGradient colors={['#4ECDC4', '#44A08D']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.buttonGradient}>
                  <Ionicons name="person-add" size={24} color="#fff" />
                  <Text style={styles.secondaryButtonText}>Create Account</Text>
                </LinearGradient>
              </TouchableOpacity>
            </>
          )}

          <View style={{ height: 30 }} />
        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FF' },
  headerGradient: { paddingBottom: 30, borderBottomLeftRadius: 40, borderBottomRightRadius: 40 },
  logoContainer: { alignItems: 'center', paddingVertical: 20 },
  logoCircle: { width: 100, height: 100, borderRadius: 50, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  logoEmoji: { fontSize: 56 },
  logoText: { fontSize: 36, fontWeight: '800', color: '#fff' },
  tagline: { fontSize: 16, color: 'rgba(255,255,255,0.9)', marginTop: 6, fontWeight: '500' },
  content: { flex: 1, paddingHorizontal: 20, marginTop: -20 },
  welcomeCard: { backgroundColor: '#fff', borderRadius: 24, padding: 20, marginBottom: 20, shadowColor: '#667eea', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.15, shadowRadius: 20, elevation: 8 },
  welcomeTitle: { fontSize: 22, fontWeight: '700', color: '#2D3436', marginBottom: 8 },
  welcomeText: { fontSize: 15, color: '#636E72', lineHeight: 22 },
  verseCard: { borderRadius: 24, overflow: 'hidden', marginBottom: 20 },
  verseGradient: { padding: 22, borderRadius: 24 },
  verseHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 14 },
  verseSunrise: { width: 32, height: 32, borderRadius: 16, backgroundColor: 'rgba(255,217,61,0.15)', alignItems: 'center', justifyContent: 'center', marginRight: 10 },
  verseLabel: { fontSize: 14, fontWeight: '700', color: '#FFD93D', flex: 1 },
  verseThemeBadge: { backgroundColor: 'rgba(255,255,255,0.1)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10 },
  verseThemeText: { fontSize: 11, fontWeight: '600', color: 'rgba(255,255,255,0.7)', textTransform: 'capitalize' },
  verseText: { fontSize: 17, fontWeight: '600', color: '#fff', lineHeight: 26, fontStyle: 'italic' },
  verseReference: { fontSize: 14, fontWeight: '700', color: '#FFD93D', marginTop: 10 },
  verseDivider: { height: 1, backgroundColor: 'rgba(255,255,255,0.1)', marginVertical: 14 },
  verseExplanation: { fontSize: 14, color: 'rgba(255,255,255,0.8)', lineHeight: 21 },
  verseShareButton: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-end', marginTop: 14, backgroundColor: 'rgba(255,217,61,0.12)', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, gap: 6 },
  verseShareText: { fontSize: 13, fontWeight: '600', color: '#FFD93D' },
  featuresGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24, gap: 8 },
  featureCard: { flex: 1, paddingVertical: 18, borderRadius: 20, alignItems: 'center', justifyContent: 'center', minHeight: 88 },
  featureIcon: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  featureLabelChat: { fontSize: 12, fontWeight: '700', color: '#FF6B6B', textAlign: 'center' },
  featureLabelVoice: { fontSize: 12, fontWeight: '700', color: '#4ECDC4', textAlign: 'center' },
  featureLabelLearn: { fontSize: 12, fontWeight: '700', color: '#FFD93D', textAlign: 'center' },
  featureLabelSafe: { fontSize: 12, fontWeight: '700', color: '#6C5CE7', textAlign: 'center' },
  primaryButton: { marginBottom: 12, borderRadius: 20, overflow: 'hidden', shadowColor: '#FF6B6B', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.4, shadowRadius: 16, elevation: 8 },
  buttonGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 18, paddingHorizontal: 24, gap: 12 },
  primaryButtonText: { color: '#fff', fontSize: 20, fontWeight: '700', flex: 1, textAlign: 'center' },
  secondaryButton: { marginBottom: 12, borderRadius: 16, overflow: 'hidden', shadowColor: '#4ECDC4', shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.3, shadowRadius: 12, elevation: 6 },
  secondaryButtonText: { color: '#fff', fontSize: 17, fontWeight: '600', marginLeft: 10 },
  dashboardButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff', paddingVertical: 16, borderRadius: 16, marginBottom: 12, borderWidth: 2, borderColor: '#6C5CE7', gap: 8 },
  dashboardButtonText: { color: '#6C5CE7', fontSize: 16, fontWeight: '600', flex: 1, textAlign: 'center' },
  logoutButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 14, gap: 8, marginBottom: 20 },
  logoutText: { fontSize: 15, color: '#FF6B6B', fontWeight: '600' },

  // Story of the Week
  storyCard: { borderRadius: 24, overflow: 'hidden', marginBottom: 20 },
  storyGradient: { padding: 22, borderRadius: 24 },
  storyHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 14 },
  storyIconCircle: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  storyLabel: { fontSize: 14, fontWeight: '700', color: 'rgba(255,255,255,0.9)' },
  storyWeek: { fontSize: 11, color: 'rgba(255,255,255,0.6)', marginTop: 2 },
  storyTitle: { fontSize: 22, fontWeight: '800', color: '#fff', marginBottom: 4 },
  storyRef: { fontSize: 13, fontWeight: '600', color: 'rgba(255,255,255,0.7)', marginBottom: 10 },
  storySummary: { fontSize: 14, color: 'rgba(255,255,255,0.85)', lineHeight: 20, marginBottom: 14 },
  storyThemePill: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 12, gap: 5 },
  storyThemeText: { fontSize: 12, fontWeight: '700', color: '#fff' },
  storyFooter: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  storyProgressRow: { flexDirection: 'row', gap: 6 },
  storyProgressPill: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 10, gap: 4 },
  storyProgressText: { fontSize: 11, fontWeight: '700', color: '#fff' },
  // Reading Night Banner
  readingNightBanner: { borderRadius: 16, overflow: 'hidden', marginBottom: 16 },
  readingNightGradient: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 16, gap: 12 },
  readingNightBannerTitle: { fontSize: 15, fontWeight: '700', color: '#fff' },
  readingNightBannerText: { fontSize: 12, color: 'rgba(255,255,255,0.85)', marginTop: 2 },
});
