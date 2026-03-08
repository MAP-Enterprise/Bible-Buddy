import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Dimensions,
  StatusBar,
  ScrollView,
  Platform,
  Share,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons, MaterialCommunityIcons, FontAwesome5 } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { storage } from '../helpers/storage';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const { width: screenWidth } = Dimensions.get('window');

interface VerseOfTheDay {
  date: string;
  verse: string;
  reference: string;
  theme: string;
  explanation: string;
}

export default function HomeScreen() {
  const bounceAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const [verseData, setVerseData] = useState<VerseOfTheDay | null>(null);
  const [verseLoading, setVerseLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Entrance animations
    Animated.parallel([
      Animated.spring(scaleAnim, {
        toValue: 1,
        tension: 50,
        friction: 7,
        useNativeDriver: true,
      }),
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
    ]).start();

    // Continuous bounce
    Animated.loop(
      Animated.sequence([
        Animated.timing(bounceAnim, { toValue: -12, duration: 1200, useNativeDriver: true }),
        Animated.timing(bounceAnim, { toValue: 0, duration: 1200, useNativeDriver: true }),
      ])
    ).start();

    // Fetch verse of the day
    fetchVerseOfTheDay();
  }, []);

  const fetchVerseOfTheDay = async () => {
    try {
      const savedTier = await storage.getItem('ageTier');
      const ageTier = savedTier || '7-9';
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
        // Fallback
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } else {
      Share.share({ message: shareText });
    }
  };

  const features = [
    { icon: 'chatbubbles', color: '#FF6B6B', bg: '#FFE8E8', label: 'Chat' },
    { icon: 'mic', color: '#4ECDC4', bg: '#E0F7F5', label: 'Voice' },
    { icon: 'book', color: '#FFD93D', bg: '#FFF8E0', label: 'Learn' },
    { icon: 'shield-checkmark', color: '#6C5CE7', bg: '#EDE9FE', label: 'Safe' },
  ];

  const teachers = [
    { name: 'Apostle Selman', color: '#FF6B6B', emoji: '🎤' },
    { name: 'Stephanie Ike', color: '#4ECDC4', emoji: '💜' },
    { name: 'Steven Furtick', color: '#FFD93D', emoji: '🔥' },
    { name: 'Priscilla Shirer', color: '#6C5CE7', emoji: '⚔️' },
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
              <Text style={styles.logoEmoji}>📖</Text>
            </View>
            <Text style={styles.logoText}>Bible Buddy</Text>
            <Text style={styles.tagline}>Your Friendly Faith Companion! ✨</Text>
          </Animated.View>
        </SafeAreaView>
      </LinearGradient>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <Animated.View style={{ opacity: fadeAnim }}>
          {/* Welcome Card */}
          <View style={styles.welcomeCard}>
            <Text style={styles.welcomeTitle}>👋 Hey there, friend!</Text>
            <Text style={styles.welcomeText}>
              I'm here to help you learn about God, Jesus, and the Bible in a fun way!
            </Text>
          </View>

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

                <TouchableOpacity
                  style={styles.verseShareButton}
                  onPress={handleShareVerse}
                  activeOpacity={0.7}
                  data-testid="share-verse-btn"
                >
                  <Ionicons name={copied ? "checkmark-circle" : "share-social"} size={18} color="#FFD93D" />
                  <Text style={styles.verseShareText}>{copied ? 'Copied!' : 'Share Verse'}</Text>
                </TouchableOpacity>
              </LinearGradient>
            </View>
          ) : null}

          {/* Features Grid */}
          <View style={styles.featuresGrid}>
            {features.map((feature, index) => (
              <View key={index} style={[styles.featureCard, { backgroundColor: feature.bg }]} data-testid={`feature-${feature.label.toLowerCase()}`}>
                <View style={[styles.featureIcon, { backgroundColor: feature.color }]}>
                  <Ionicons name={feature.icon as any} size={24} color="#fff" />
                </View>
                <Text style={{ fontSize: 12, fontWeight: '700', color: feature.color, textAlign: 'center' }}>{feature.label}</Text>
              </View>
            ))}
          </View>

          {/* Main CTA Buttons */}
          <TouchableOpacity
            style={styles.primaryButton}
            onPress={() => router.push('/chat')}
            activeOpacity={0.9}
          >
            <LinearGradient
              colors={['#FF6B6B', '#FF8E53']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.buttonGradient}
            >
              <Ionicons name="chatbubble-ellipses" size={28} color="#fff" />
              <Text style={styles.primaryButtonText}>Start Chatting!</Text>
              <Ionicons name="arrow-forward-circle" size={28} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => router.push('/onboarding')}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={['#4ECDC4', '#44A08D']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.buttonGradient}
            >
              <Ionicons name="person-add" size={24} color="#fff" />
              <Text style={styles.secondaryButtonText}>Set Up Profile</Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.dashboardButton}
            onPress={() => router.push('/parent-dashboard')}
            activeOpacity={0.8}
          >
            <Ionicons name="people" size={22} color="#6C5CE7" />
            <Text style={styles.dashboardButtonText}>Parent Dashboard</Text>
            <Ionicons name="chevron-forward" size={20} color="#6C5CE7" />
          </TouchableOpacity>

          {/* Teachers Section */}
          <View style={styles.teachersSection}>
            <Text style={styles.sectionTitle}>✨ Wisdom from Amazing Teachers</Text>
            <View style={styles.teachersGrid}>
              {teachers.map((teacher, index) => (
                <View key={index} style={styles.teacherChip}>
                  <Text style={styles.teacherEmoji}>{teacher.emoji}</Text>
                  <Text style={styles.teacherName}>{teacher.name}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* Bottom Spacer */}
          <View style={{ height: 30 }} />
        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F9FF',
  },
  headerGradient: {
    paddingBottom: 30,
    borderBottomLeftRadius: 40,
    borderBottomRightRadius: 40,
  },
  logoContainer: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  logoCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  logoEmoji: {
    fontSize: 56,
  },
  logoText: {
    fontSize: 36,
    fontWeight: '800',
    color: '#fff',
    textShadowColor: 'rgba(0,0,0,0.2)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 4,
  },
  tagline: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.9)',
    marginTop: 6,
    fontWeight: '500',
  },
  content: {
    flex: 1,
    paddingHorizontal: 20,
    marginTop: -20,
  },
  welcomeCard: {
    backgroundColor: '#fff',
    borderRadius: 24,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#667eea',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.15,
    shadowRadius: 20,
    elevation: 8,
  },
  welcomeTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#2D3436',
    marginBottom: 8,
  },
  welcomeText: {
    fontSize: 15,
    color: '#636E72',
    lineHeight: 22,
  },
  verseCard: {
    borderRadius: 24,
    overflow: 'hidden',
    marginBottom: 20,
  },
  verseGradient: {
    padding: 22,
    borderRadius: 24,
  },
  verseHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  verseSunrise: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255,217,61,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  verseLabel: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFD93D',
    flex: 1,
  },
  verseThemeBadge: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
  },
  verseThemeText: {
    fontSize: 11,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.7)',
    textTransform: 'capitalize',
  },
  verseText: {
    fontSize: 17,
    fontWeight: '600',
    color: '#fff',
    lineHeight: 26,
    fontStyle: 'italic',
  },
  verseReference: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFD93D',
    marginTop: 10,
  },
  verseDivider: {
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.1)',
    marginVertical: 14,
  },
  verseExplanation: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    lineHeight: 21,
  },
  verseShareButton: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-end',
    marginTop: 14,
    backgroundColor: 'rgba(255,217,61,0.12)',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 16,
    gap: 6,
  },
  verseShareText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#FFD93D',
  },
  featuresGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  featureCard: {
    width: '22%' as any,
    paddingVertical: 16,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  featureIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  primaryButton: {
    marginBottom: 12,
    borderRadius: 20,
    overflow: 'hidden',
    shadowColor: '#FF6B6B',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4,
    shadowRadius: 16,
    elevation: 8,
  },
  buttonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 18,
    paddingHorizontal: 24,
    gap: 12,
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '700',
    flex: 1,
    textAlign: 'center',
  },
  secondaryButton: {
    marginBottom: 12,
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#4ECDC4',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 6,
  },
  secondaryButtonText: {
    color: '#fff',
    fontSize: 17,
    fontWeight: '600',
    marginLeft: 10,
  },
  dashboardButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    paddingVertical: 16,
    borderRadius: 16,
    marginBottom: 24,
    borderWidth: 2,
    borderColor: '#6C5CE7',
    gap: 8,
  },
  dashboardButtonText: {
    color: '#6C5CE7',
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
    textAlign: 'center',
  },
  teachersSection: {
    backgroundColor: '#fff',
    borderRadius: 24,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 4,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#2D3436',
    marginBottom: 16,
    textAlign: 'center',
  },
  teachersGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 10,
  },
  teacherChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F8F9FF',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 20,
    gap: 6,
  },
  teacherEmoji: {
    fontSize: 16,
  },
  teacherName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#636E72',
  },
});
