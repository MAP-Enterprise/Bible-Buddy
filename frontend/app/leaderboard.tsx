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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuthContext } from '../contexts/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface LeaderboardEntry {
  rank: number;
  child_id: string;
  name: string;
  age_tier: string;
  challenge_stats: {
    total_played: number;
    average_score: number;
    perfect_scores: number;
    current_streak: number;
    best_streak: number;
  };
  chat_stats: {
    total_conversations: number;
    total_messages: number;
  };
}

interface FamilyStats {
  total_children: number;
  total_challenges_completed: number;
  family_average_score: number;
  total_perfect_scores: number;
}

const RANK_COLORS = ['#FFD93D', '#C0C0C0', '#CD7F32'];
const RANK_ICONS: Array<'trophy' | 'medal' | 'ribbon'> = ['trophy', 'medal', 'ribbon'];

export default function LeaderboardScreen() {
  const { token } = useAuthContext();
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [familyStats, setFamilyStats] = useState<FamilyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    fetchLeaderboard();
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
  }, []);

  const fetchLeaderboard = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/leaderboard`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setLeaderboard(data.leaderboard || []);
        setFamilyStats(data.family_stats || null);
      }
    } catch (e) {
      console.log('Leaderboard fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  const renderChild = (entry: LeaderboardEntry, index: number) => {
    const isTop3 = index < 3;
    const color = RANK_COLORS[index] || '#6C5CE7';
    const icon = RANK_ICONS[index] || 'star';
    const s = entry.challenge_stats;

    return (
      <Animated.View
        key={entry.child_id}
        style={[styles.childCard, isTop3 && { borderLeftWidth: 4, borderLeftColor: color }]}
        data-testid={`leaderboard-entry-${index}`}
      >
        <View style={styles.rankSection}>
          <View style={[styles.rankBadge, { backgroundColor: isTop3 ? `${color}30` : '#F0F0F0' }]}>
            {isTop3 ? (
              <Ionicons name={icon} size={22} color={color} />
            ) : (
              <Text style={styles.rankNumber}>{entry.rank}</Text>
            )}
          </View>
        </View>

        <View style={styles.childInfo}>
          <Text style={styles.childName}>{entry.name}</Text>
          <Text style={styles.ageBadge}>{entry.age_tier} yrs</Text>
        </View>

        <View style={styles.statsGrid}>
          <View style={styles.miniStat}>
            <Text style={[styles.miniStatValue, { color: '#6C5CE7' }]}>{s.average_score}%</Text>
            <Text style={styles.miniStatLabel}>Avg</Text>
          </View>
          <View style={styles.miniStat}>
            <Text style={[styles.miniStatValue, { color: '#FF6B6B' }]}>{s.current_streak}</Text>
            <Text style={styles.miniStatLabel}>Streak</Text>
          </View>
          <View style={styles.miniStat}>
            <Text style={[styles.miniStatValue, { color: '#4ECDC4' }]}>{s.perfect_scores}</Text>
            <Text style={styles.miniStatLabel}>Perfect</Text>
          </View>
          <View style={styles.miniStat}>
            <Text style={[styles.miniStatValue, { color: '#FFD93D' }]}>{s.total_played}</Text>
            <Text style={styles.miniStatLabel}>Played</Text>
          </View>
        </View>
      </Animated.View>
    );
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      <LinearGradient colors={['#FF6B6B', '#FF8E53']} style={styles.header}>
        <SafeAreaView edges={['top']} style={styles.headerContent}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} data-testid="leaderboard-back-btn">
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Ionicons name="trophy" size={24} color="#FFD93D" />
            <Text style={styles.headerTitle}>Family Leaderboard</Text>
          </View>
          <View style={{ width: 40 }} />
        </SafeAreaView>
      </LinearGradient>

      <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent} showsVerticalScrollIndicator={false}>
        <Animated.View style={{ opacity: fadeAnim }}>
          {loading ? (
            <View style={styles.loadingBox}>
              <ActivityIndicator size="large" color="#FF6B6B" />
              <Text style={styles.loadingText}>Loading leaderboard...</Text>
            </View>
          ) : leaderboard.length === 0 ? (
            <View style={styles.emptyBox}>
              <Ionicons name="trophy-outline" size={64} color="#DDD" />
              <Text style={styles.emptyTitle}>No Challenges Yet</Text>
              <Text style={styles.emptyDesc}>Complete the daily verse challenge to start the leaderboard!</Text>
              <TouchableOpacity
                style={styles.startBtn}
                onPress={() => router.push('/verse-challenge')}
                data-testid="start-challenge-btn"
              >
                <LinearGradient colors={['#FF6B6B', '#FF8E53']} style={styles.startBtnGradient}>
                  <Text style={styles.startBtnText}>Start Challenge</Text>
                </LinearGradient>
              </TouchableOpacity>
            </View>
          ) : (
            <>
              {/* Family Summary */}
              {familyStats && (
                <View style={styles.familySummary} data-testid="family-stats">
                  <View style={styles.familyStat}>
                    <Text style={styles.familyStatValue}>{familyStats.total_challenges_completed}</Text>
                    <Text style={styles.familyStatLabel}>Total Challenges</Text>
                  </View>
                  <View style={styles.familyStatDivider} />
                  <View style={styles.familyStat}>
                    <Text style={styles.familyStatValue}>{familyStats.family_average_score}%</Text>
                    <Text style={styles.familyStatLabel}>Family Average</Text>
                  </View>
                  <View style={styles.familyStatDivider} />
                  <View style={styles.familyStat}>
                    <Text style={styles.familyStatValue}>{familyStats.total_perfect_scores}</Text>
                    <Text style={styles.familyStatLabel}>Perfect Scores</Text>
                  </View>
                </View>
              )}

              {/* Leaderboard */}
              {leaderboard.map((entry, i) => renderChild(entry, i))}
            </>
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
  headerCenter: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#fff' },
  body: { flex: 1 },
  bodyContent: { padding: 20 },

  // Family Summary
  familySummary: { flexDirection: 'row', backgroundColor: '#fff', borderRadius: 20, padding: 18, marginBottom: 20, alignItems: 'center', justifyContent: 'space-around', shadowColor: '#FF6B6B', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 12, elevation: 4 },
  familyStat: { alignItems: 'center' },
  familyStatValue: { fontSize: 24, fontWeight: '900', color: '#FF6B6B' },
  familyStatLabel: { fontSize: 11, color: '#636E72', fontWeight: '600', marginTop: 2 },
  familyStatDivider: { width: 1, height: 36, backgroundColor: '#F0F0F0' },

  // Child Card
  childCard: { backgroundColor: '#fff', borderRadius: 20, padding: 16, marginBottom: 12, flexDirection: 'row', alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 3, gap: 12 },
  rankSection: { alignItems: 'center' },
  rankBadge: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  rankNumber: { fontSize: 18, fontWeight: '800', color: '#636E72' },
  childInfo: { flex: 1 },
  childName: { fontSize: 17, fontWeight: '700', color: '#2D3436' },
  ageBadge: { fontSize: 12, color: '#636E72', marginTop: 2 },
  statsGrid: { flexDirection: 'row', gap: 10 },
  miniStat: { alignItems: 'center' },
  miniStatValue: { fontSize: 16, fontWeight: '800' },
  miniStatLabel: { fontSize: 9, color: '#AAA', fontWeight: '600' },

  // Loading/Empty
  loadingBox: { alignItems: 'center', padding: 60 },
  loadingText: { fontSize: 15, color: '#636E72', marginTop: 12 },
  emptyBox: { alignItems: 'center', padding: 40 },
  emptyTitle: { fontSize: 22, fontWeight: '800', color: '#2D3436', marginTop: 16 },
  emptyDesc: { fontSize: 15, color: '#636E72', textAlign: 'center', marginTop: 8, maxWidth: 280 },
  startBtn: { marginTop: 20, borderRadius: 16, overflow: 'hidden' },
  startBtnGradient: { paddingHorizontal: 24, paddingVertical: 14 },
  startBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
});
