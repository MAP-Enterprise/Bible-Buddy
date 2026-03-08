import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
  Animated,
  Dimensions,
  StatusBar,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const { width } = Dimensions.get('window');

// Storage helper for cross-platform support
const storage = {
  async getItem(key: string): Promise<string | null> {
    if (Platform.OS === 'web') {
      return localStorage.getItem(key);
    }
    const AsyncStorage = require('@react-native-async-storage/async-storage').default;
    return AsyncStorage.getItem(key);
  },
  async setItem(key: string, value: string): Promise<void> {
    if (Platform.OS === 'web') {
      localStorage.setItem(key, value);
      return;
    }
    const AsyncStorage = require('@react-native-async-storage/async-storage').default;
    return AsyncStorage.setItem(key, value);
  },
};

interface Conversation {
  id: string;
  messages: Array<{ role: string; content: string; timestamp: string }>;
  created_at: string;
  updated_at: string;
}

export default function ParentDashboardScreen() {
  const [childId, setChildId] = useState<string | null>(null);
  const [childName, setChildName] = useState('');
  const [ageTier, setAgeTier] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    loadChildData();
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
  }, []);

  const loadChildData = async () => {
    try {
      const childData = await storage.getItem('currentChild');
      if (childData) {
        const child = JSON.parse(childData);
        setChildId(child.child_id);
        setChildName(child.name);
        setAgeTier(child.age_tier);
        await fetchConversations(child.child_id);
      }
    } catch (error) {
      console.error('Load error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchConversations = async (id: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/sessions/${id}`);
      if (res.ok) {
        const data = await res.json();
        setConversations(data.sessions || []);
      }
    } catch (error) {
      console.error('Fetch error:', error);
    }
  };

  const onRefresh = async () => {
    setIsRefreshing(true);
    if (childId) await fetchConversations(childId);
    setIsRefreshing(false);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const totalMessages = conversations.reduce((acc, c) => acc + (c.messages?.length || 0), 0);
  const topics: { [key: string]: number } = {};
  conversations.forEach((c) => {
    c.messages?.forEach((m) => {
      if (m.role === 'user') {
        ['jesus', 'god', 'bible', 'prayer', 'heaven', 'love', 'faith'].forEach(topic => {
          if (m.content.toLowerCase().includes(topic)) topics[topic] = (topics[topic] || 0) + 1;
        });
      }
    });
  });
  const topTopics = Object.entries(topics).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([t]) => t);

  if (isLoading) {
    return (
      <View style={[styles.container, styles.loadingContainer]}>
        <ActivityIndicator size="large" color="#667eea" />
      </View>
    );
  }

  if (selectedConversation) {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" />
        <LinearGradient colors={['#667eea', '#764ba2']} style={styles.header}>
          <SafeAreaView edges={['top']} style={styles.headerContent}>
            <TouchableOpacity onPress={() => setSelectedConversation(null)} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color="#fff" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Conversation</Text>
            <View style={{ width: 40 }} />
          </SafeAreaView>
        </LinearGradient>
        
        <ScrollView style={styles.conversationDetail}>
          <Text style={styles.conversationDateHeader}>{formatDate(selectedConversation.created_at)}</Text>
          {selectedConversation.messages.map((msg, i) => (
            <View key={i} style={[styles.messageCard, msg.role === 'user' ? styles.userMessageCard : styles.assistantMessageCard]}>
              <View style={styles.messageHeader}>
                <View style={[styles.roleIcon, { backgroundColor: msg.role === 'user' ? '#FF6B6B' : '#4ECDC4' }]}>
                  <Ionicons name={msg.role === 'user' ? 'person' : 'book'} size={14} color="#fff" />
                </View>
                <Text style={styles.roleName}>{msg.role === 'user' ? childName : 'Bible Buddy'}</Text>
              </View>
              <Text style={styles.messageText}>{msg.content}</Text>
            </View>
          ))}
          <View style={{ height: 30 }} />
        </ScrollView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Header */}
      <LinearGradient colors={['#667eea', '#764ba2']} style={styles.header}>
        <SafeAreaView edges={['top']} style={styles.headerContent}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Parent Dashboard</Text>
          <View style={{ width: 40 }} />
        </SafeAreaView>
      </LinearGradient>

      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.contentContainer}
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={onRefresh} colors={['#667eea']} />}
      >
        <Animated.View style={{ opacity: fadeAnim }}>
          {/* Child Profile Card */}
          <View style={styles.profileCard}>
            <LinearGradient colors={['#FF6B6B', '#FF8E53']} style={styles.avatarGradient}>
              <Text style={styles.avatarText}>{childName?.[0]?.toUpperCase() || '?'}</Text>
            </LinearGradient>
            <View style={styles.profileInfo}>
              <Text style={styles.profileName}>{childName || 'No Profile'}</Text>
              <View style={styles.ageBadge}>
                <Text style={styles.ageBadgeText}>Age: {ageTier || '?'} years</Text>
              </View>
            </View>
            <TouchableOpacity onPress={() => router.push('/onboarding')} style={styles.editButton}>
              <Ionicons name="create" size={20} color="#6C5CE7" />
            </TouchableOpacity>
          </View>

          {/* Stats Grid */}
          <View style={styles.statsGrid}>
            <View style={[styles.statCard, { backgroundColor: '#FFE8E8' }]}>
              <Ionicons name="chatbubbles" size={28} color="#FF6B6B" />
              <Text style={[styles.statNumber, { color: '#FF6B6B' }]}>{conversations.length}</Text>
              <Text style={styles.statLabel}>Conversations</Text>
            </View>
            <View style={[styles.statCard, { backgroundColor: '#E0F7F5' }]}>
              <Ionicons name="chatbox" size={28} color="#4ECDC4" />
              <Text style={[styles.statNumber, { color: '#4ECDC4' }]}>{totalMessages}</Text>
              <Text style={styles.statLabel}>Messages</Text>
            </View>
          </View>

          {/* Topics Section */}
          {topTopics.length > 0 && (
            <View style={styles.topicsCard}>
              <Text style={styles.sectionTitle}>🔥 Popular Topics</Text>
              <View style={styles.topicsList}>
                {topTopics.map((topic, i) => {
                  const colors = ['#FF6B6B', '#4ECDC4', '#FFD93D', '#6C5CE7', '#FF8E53'];
                  return (
                    <View key={i} style={[styles.topicChip, { backgroundColor: `${colors[i]}20` }]}>
                      <Text style={[styles.topicText, { color: colors[i] }]}>{topic}</Text>
                    </View>
                  );
                })}
              </View>
            </View>
          )}

          {/* Conversations List */}
          <View style={styles.conversationsSection}>
            <Text style={styles.sectionTitle}>📚 Recent Conversations</Text>
            {conversations.length === 0 ? (
              <View style={styles.emptyState}>
                <View style={styles.emptyIcon}>
                  <Ionicons name="chatbubbles-outline" size={48} color="#CCC" />
                </View>
                <Text style={styles.emptyText}>No conversations yet</Text>
                <Text style={styles.emptySubtext}>Start chatting to see history here!</Text>
              </View>
            ) : (
              conversations.slice(0, 10).map((conv, i) => (
                <TouchableOpacity
                  key={conv.id}
                  style={styles.conversationCard}
                  onPress={() => setSelectedConversation(conv)}
                  activeOpacity={0.7}
                >
                  <View style={[styles.conversationIcon, { backgroundColor: ['#FFE8E8', '#E0F7F5', '#FFF8E0', '#EDE9FE'][i % 4] }]}>
                    <Ionicons name="chatbubble" size={20} color={['#FF6B6B', '#4ECDC4', '#FFD93D', '#6C5CE7'][i % 4]} />
                  </View>
                  <View style={styles.conversationInfo}>
                    <Text style={styles.conversationPreview} numberOfLines={1}>
                      {conv.messages?.[0]?.content || 'Empty conversation'}
                    </Text>
                    <Text style={styles.conversationMeta}>
                      {conv.messages?.length || 0} messages • {formatDate(conv.updated_at)}
                    </Text>
                  </View>
                  <Ionicons name="chevron-forward" size={22} color="#CCC" />
                </TouchableOpacity>
              ))
            )}
          </View>

          {/* Actions */}
          <TouchableOpacity style={styles.actionButton} onPress={() => router.push('/chat')} activeOpacity={0.9}>
            <LinearGradient colors={['#4ECDC4', '#44A08D']} style={styles.actionGradient}>
              <Ionicons name="chatbubble-ellipses" size={24} color="#fff" />
              <Text style={styles.actionText}>Open Chat</Text>
            </LinearGradient>
          </TouchableOpacity>

          <View style={{ height: 30 }} />
        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FF' },
  loadingContainer: { alignItems: 'center', justifyContent: 'center' },
  header: { paddingBottom: 16 },
  headerContent: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: 8 },
  backButton: { width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#fff' },
  content: { flex: 1 },
  contentContainer: { padding: 20 },
  profileCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 20, borderRadius: 24, marginBottom: 20, shadowColor: '#667eea', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.15, shadowRadius: 20, elevation: 8 },
  avatarGradient: { width: 60, height: 60, borderRadius: 30, alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: 26, fontWeight: '800', color: '#fff' },
  profileInfo: { flex: 1, marginLeft: 16 },
  profileName: { fontSize: 22, fontWeight: '700', color: '#2D3436' },
  ageBadge: { backgroundColor: '#EDE9FE', paddingHorizontal: 12, paddingVertical: 4, borderRadius: 12, alignSelf: 'flex-start', marginTop: 6 },
  ageBadgeText: { fontSize: 13, fontWeight: '600', color: '#6C5CE7' },
  editButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#EDE9FE', alignItems: 'center', justifyContent: 'center' },
  statsGrid: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  statCard: { flex: 1, padding: 20, borderRadius: 20, alignItems: 'center' },
  statNumber: { fontSize: 36, fontWeight: '800', marginTop: 8 },
  statLabel: { fontSize: 13, color: '#636E72', marginTop: 4, fontWeight: '600' },
  topicsCard: { backgroundColor: '#fff', borderRadius: 20, padding: 20, marginBottom: 20 },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: '#2D3436', marginBottom: 14 },
  topicsList: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  topicChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16 },
  topicText: { fontSize: 14, fontWeight: '700', textTransform: 'capitalize' },
  conversationsSection: { marginBottom: 20 },
  emptyState: { alignItems: 'center', paddingVertical: 40 },
  emptyIcon: { width: 80, height: 80, borderRadius: 40, backgroundColor: '#F0F0F0', alignItems: 'center', justifyContent: 'center', marginBottom: 16 },
  emptyText: { fontSize: 18, fontWeight: '700', color: '#636E72' },
  emptySubtext: { fontSize: 14, color: '#AAA', marginTop: 6 },
  conversationCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 16, borderRadius: 16, marginBottom: 10, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  conversationIcon: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', marginRight: 14 },
  conversationInfo: { flex: 1 },
  conversationPreview: { fontSize: 15, fontWeight: '600', color: '#2D3436' },
  conversationMeta: { fontSize: 12, color: '#AAA', marginTop: 4 },
  actionButton: { borderRadius: 20, overflow: 'hidden', shadowColor: '#4ECDC4', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.35, shadowRadius: 16, elevation: 8 },
  actionGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 18, gap: 10 },
  actionText: { color: '#fff', fontSize: 18, fontWeight: '700' },
  conversationDetail: { flex: 1, padding: 20 },
  conversationDateHeader: { fontSize: 14, fontWeight: '600', color: '#AAA', textAlign: 'center', marginBottom: 20 },
  messageCard: { padding: 16, borderRadius: 16, marginBottom: 12 },
  userMessageCard: { backgroundColor: '#FFE8E8', marginLeft: 40 },
  assistantMessageCard: { backgroundColor: '#fff', marginRight: 40, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 2 },
  messageHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  roleIcon: { width: 26, height: 26, borderRadius: 13, alignItems: 'center', justifyContent: 'center', marginRight: 8 },
  roleName: { fontSize: 14, fontWeight: '700', color: '#2D3436' },
  messageText: { fontSize: 15, color: '#2D3436', lineHeight: 22 },
});
