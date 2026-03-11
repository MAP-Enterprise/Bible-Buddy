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
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuthContext, } from '../contexts/AuthContext';
import type { Child } from '../hooks/useAuth';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Conversation {
  id: string;
  child_id: string;
  messages: Array<{ role: string; content: string; timestamp: string }>;
  created_at: string;
  updated_at: string;
}

interface ChildStats {
  child_id: string;
  child_name: string;
  total_conversations: number;
  total_messages: number;
  most_asked_topics: string[];
  last_active: string | null;
}

export default function ParentDashboardScreen() {
  const { isAuthenticated, user, token, children: childProfiles, activeChild, setActiveChild, refreshChildren } = useAuthContext();
  const [stats, setStats] = useState<ChildStats | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [showChildPicker, setShowChildPicker] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
  }, []);

  useEffect(() => {
    if (activeChild && token) {
      loadChildData(activeChild.child_id);
    } else {
      setIsLoading(false);
    }
  }, [activeChild?.child_id]);

  const authHeaders = () => ({
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  });

  const loadChildData = async (childId: string) => {
    setIsLoading(true);
    try {
      const [statsRes, convsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/dashboard/stats/${childId}`, { headers: authHeaders() }),
        fetch(`${BACKEND_URL}/api/dashboard/conversations/${childId}`, { headers: authHeaders() }),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (convsRes.ok) {
        const data = await convsRes.json();
        setConversations(data.conversations || []);
      }
    } catch (e) {
      console.error('Dashboard load error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const onRefresh = async () => {
    setIsRefreshing(true);
    await refreshChildren();
    if (activeChild) await loadChildData(activeChild.child_id);
    setIsRefreshing(false);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const handleSwitchChild = async (child: Child) => {
    setShowChildPicker(false);
    await setActiveChild(child);
  };

  // Not authenticated
  if (!isAuthenticated) {
    return (
      <View style={[styles.container, styles.centerContent]}>
        <StatusBar barStyle="light-content" />
        <LinearGradient colors={['#667eea', '#764ba2']} style={[StyleSheet.absoluteFill]} />
        <View style={styles.authPrompt}>
          <Ionicons name="lock-closed" size={48} color="#FFD93D" />
          <Text style={styles.authPromptTitle}>Sign In Required</Text>
          <Text style={styles.authPromptText}>Please sign in to access the Parent Dashboard</Text>
          <TouchableOpacity style={styles.authPromptButton} onPress={() => router.push('/sign-in')} data-testid="dashboard-sign-in-btn">
            <Text style={styles.authPromptButtonText}>Sign In</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  // Loading
  if (isLoading) {
    return (
      <View style={[styles.container, styles.centerContent]}>
        <ActivityIndicator size="large" color="#667eea" />
      </View>
    );
  }

  // Conversation Detail View
  if (selectedConversation) {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" />
        <LinearGradient colors={['#667eea', '#764ba2']} style={styles.header}>
          <SafeAreaView edges={['top']} style={styles.headerContent}>
            <TouchableOpacity onPress={() => setSelectedConversation(null)} style={styles.backButton} data-testid="conversation-back-btn">
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
                <Text style={styles.roleName}>{msg.role === 'user' ? (activeChild?.name || 'Child') : 'Bible Buddy'}</Text>
              </View>
              <Text style={styles.messageText}>{msg.content}</Text>
            </View>
          ))}
          <View style={{ height: 30 }} />
        </ScrollView>
      </View>
    );
  }

  // Main Dashboard View
  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      <LinearGradient colors={['#667eea', '#764ba2']} style={styles.header}>
        <SafeAreaView edges={['top']} style={styles.headerContent}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton} data-testid="dashboard-back-btn">
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
          {/* Parent Info */}
          <View style={styles.parentCard} data-testid="parent-info-card">
            <View style={styles.parentAvatar}>
              <Ionicons name="person" size={24} color="#6C5CE7" />
            </View>
            <View style={styles.parentInfo}>
              <Text style={styles.parentName}>{user?.name || 'Parent'}</Text>
              <Text style={styles.parentEmail}>{user?.email}</Text>
            </View>
          </View>

          {/* Child Selector */}
          {childProfiles.length > 0 && (
            <View style={styles.childSelectorCard} data-testid="child-selector">
              <Text style={styles.selectorLabel}>Active Profile:</Text>
              <TouchableOpacity
                style={styles.childSelectorButton}
                onPress={() => setShowChildPicker(!showChildPicker)}
                data-testid="child-selector-btn"
              >
                <LinearGradient colors={['#FF6B6B', '#FF8E53']} style={styles.childAvatar}>
                  <Text style={styles.childAvatarText}>{activeChild?.name?.[0]?.toUpperCase() || '?'}</Text>
                </LinearGradient>
                <View style={{ flex: 1 }}>
                  <Text style={styles.childSelectorName}>{activeChild?.name || 'Select child'}</Text>
                  <Text style={styles.childSelectorAge}>Age: {activeChild?.age_tier || '?'} years</Text>
                </View>
                <Ionicons name={showChildPicker ? 'chevron-up' : 'chevron-down'} size={22} color="#6C5CE7" />
              </TouchableOpacity>

              {showChildPicker && (
                <View style={styles.childPickerList}>
                  {childProfiles.map((child) => (
                    <TouchableOpacity
                      key={child.child_id}
                      style={[styles.childPickerItem, activeChild?.child_id === child.child_id && styles.childPickerActive]}
                      onPress={() => handleSwitchChild(child)}
                      data-testid={`select-child-${child.child_id}`}
                    >
                      <Text style={styles.childPickerName}>{child.name}</Text>
                      <Text style={styles.childPickerAge}>{child.age_tier} yrs</Text>
                      {activeChild?.child_id === child.child_id && (
                        <Ionicons name="checkmark-circle" size={20} color="#4ECDC4" />
                      )}
                    </TouchableOpacity>
                  ))}
                  <TouchableOpacity
                    style={styles.addChildItem}
                    onPress={() => { setShowChildPicker(false); router.push('/onboarding'); }}
                    data-testid="add-child-from-dashboard-btn"
                  >
                    <Ionicons name="add-circle" size={20} color="#6C5CE7" />
                    <Text style={styles.addChildText}>Add Another Child</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          )}

          {/* No children state */}
          {childProfiles.length === 0 && (
            <View style={styles.emptyChildState} data-testid="no-children-state">
              <Ionicons name="person-add" size={48} color="#CCC" />
              <Text style={styles.emptyChildTitle}>No child profiles yet</Text>
              <Text style={styles.emptyChildText}>Add a child to start tracking their Bible learning journey</Text>
              <TouchableOpacity style={styles.addFirstChildBtn} onPress={() => router.push('/onboarding')} data-testid="add-first-child-btn">
                <LinearGradient colors={['#4ECDC4', '#44A08D']} style={styles.addFirstChildGradient}>
                  <Ionicons name="person-add" size={20} color="#fff" />
                  <Text style={styles.addFirstChildText}>Add Child Profile</Text>
                </LinearGradient>
              </TouchableOpacity>
            </View>
          )}

          {/* Stats Grid */}
          {activeChild && (
            <>
              <View style={styles.statsGrid} data-testid="stats-grid">
                <View style={[styles.statCard, { backgroundColor: '#FFE8E8' }]}>
                  <Ionicons name="chatbubbles" size={28} color="#FF6B6B" />
                  <Text style={[styles.statNumber, { color: '#FF6B6B' }]}>{stats?.total_conversations || 0}</Text>
                  <Text style={styles.statLabel}>Conversations</Text>
                </View>
                <View style={[styles.statCard, { backgroundColor: '#E0F7F5' }]}>
                  <Ionicons name="chatbox" size={28} color="#4ECDC4" />
                  <Text style={[styles.statNumber, { color: '#4ECDC4' }]}>{stats?.total_messages || 0}</Text>
                  <Text style={styles.statLabel}>Messages</Text>
                </View>
              </View>

              {/* Topics Section */}
              {stats?.most_asked_topics && stats.most_asked_topics.length > 0 && (
                <View style={styles.topicsCard} data-testid="topics-card">
                  <Text style={styles.sectionTitle}>Popular Topics</Text>
                  <View style={styles.topicsList}>
                    {stats.most_asked_topics.map((topic, i) => {
                      const colors = ['#FF6B6B', '#4ECDC4', '#FFD93D', '#6C5CE7', '#FF8E53'];
                      return (
                        <View key={i} style={[styles.topicChip, { backgroundColor: `${colors[i % 5]}20` }]}>
                          <Text style={[styles.topicText, { color: colors[i % 5] }]}>{topic}</Text>
                        </View>
                      );
                    })}
                  </View>
                </View>
              )}

              {/* Conversations List */}
              <View style={styles.conversationsSection} data-testid="conversations-list">
                <Text style={styles.sectionTitle}>Recent Conversations</Text>
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
                      data-testid={`conversation-card-${i}`}
                    >
                      <View style={[styles.conversationIcon, { backgroundColor: ['#FFE8E8', '#E0F7F5', '#FFF8E0', '#EDE9FE'][i % 4] }]}>
                        <Ionicons name="chatbubble" size={20} color={['#FF6B6B', '#4ECDC4', '#FFD93D', '#6C5CE7'][i % 4]} />
                      </View>
                      <View style={styles.conversationInfo}>
                        <Text style={styles.conversationPreview} numberOfLines={1}>
                          {conv.messages?.[0]?.content || 'Empty conversation'}
                        </Text>
                        <Text style={styles.conversationMeta}>
                          {conv.messages?.length || 0} messages {conv.updated_at ? `\u2022 ${formatDate(conv.updated_at)}` : ''}
                        </Text>
                      </View>
                      <Ionicons name="chevron-forward" size={22} color="#CCC" />
                    </TouchableOpacity>
                  ))
                )}
              </View>
            </>
          )}

          {/* Open Chat CTA */}
          {activeChild && (
            <TouchableOpacity style={styles.actionButton} onPress={() => router.push('/chat')} activeOpacity={0.9} data-testid="open-chat-btn">
              <LinearGradient colors={['#4ECDC4', '#44A08D']} style={styles.actionGradient}>
                <Ionicons name="chatbubble-ellipses" size={24} color="#fff" />
                <Text style={styles.actionText}>Open Chat</Text>
              </LinearGradient>
            </TouchableOpacity>
          )}

          <View style={{ height: 30 }} />
        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FF' },
  centerContent: { alignItems: 'center', justifyContent: 'center' },
  header: { paddingBottom: 16 },
  headerContent: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: 8 },
  backButton: { width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.2)', alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#fff' },
  content: { flex: 1 },
  contentContainer: { padding: 20 },
  // Auth prompt
  authPrompt: { alignItems: 'center', padding: 40 },
  authPromptTitle: { fontSize: 24, fontWeight: '800', color: '#fff', marginTop: 16 },
  authPromptText: { fontSize: 16, color: 'rgba(255,255,255,0.8)', marginTop: 8, textAlign: 'center' },
  authPromptButton: { backgroundColor: '#FFD93D', paddingHorizontal: 32, paddingVertical: 14, borderRadius: 20, marginTop: 24 },
  authPromptButtonText: { fontSize: 18, fontWeight: '700', color: '#2D3436' },
  // Parent card
  parentCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 16, borderRadius: 20, marginBottom: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 2 },
  parentAvatar: { width: 48, height: 48, borderRadius: 24, backgroundColor: '#EDE9FE', alignItems: 'center', justifyContent: 'center', marginRight: 14 },
  parentInfo: { flex: 1 },
  parentName: { fontSize: 18, fontWeight: '700', color: '#2D3436' },
  parentEmail: { fontSize: 13, color: '#999', marginTop: 2 },
  // Child selector
  childSelectorCard: { backgroundColor: '#fff', borderRadius: 20, padding: 16, marginBottom: 20, shadowColor: '#667eea', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.12, shadowRadius: 12, elevation: 4 },
  selectorLabel: { fontSize: 13, fontWeight: '600', color: '#999', marginBottom: 10 },
  childSelectorButton: { flexDirection: 'row', alignItems: 'center' },
  childAvatar: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  childAvatarText: { fontSize: 20, fontWeight: '800', color: '#fff' },
  childSelectorName: { fontSize: 18, fontWeight: '700', color: '#2D3436' },
  childSelectorAge: { fontSize: 13, color: '#636E72', marginTop: 2 },
  childPickerList: { marginTop: 12, borderTopWidth: 1, borderTopColor: '#F0F0F0', paddingTop: 12 },
  childPickerItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 8, borderRadius: 12 },
  childPickerActive: { backgroundColor: '#F0FFF5' },
  childPickerName: { flex: 1, fontSize: 16, fontWeight: '600', color: '#2D3436' },
  childPickerAge: { fontSize: 13, color: '#999', marginRight: 8 },
  addChildItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 8, gap: 8, borderTopWidth: 1, borderTopColor: '#F0F0F0', marginTop: 4 },
  addChildText: { fontSize: 15, fontWeight: '600', color: '#6C5CE7' },
  // Empty child state
  emptyChildState: { alignItems: 'center', paddingVertical: 40, backgroundColor: '#fff', borderRadius: 24, marginBottom: 20 },
  emptyChildTitle: { fontSize: 20, fontWeight: '700', color: '#2D3436', marginTop: 16 },
  emptyChildText: { fontSize: 14, color: '#999', marginTop: 6, textAlign: 'center', paddingHorizontal: 30 },
  addFirstChildBtn: { borderRadius: 16, overflow: 'hidden', marginTop: 20 },
  addFirstChildGradient: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 24, gap: 8 },
  addFirstChildText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  // Stats
  statsGrid: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  statCard: { flex: 1, padding: 20, borderRadius: 20, alignItems: 'center' },
  statNumber: { fontSize: 36, fontWeight: '800', marginTop: 8 },
  statLabel: { fontSize: 13, color: '#636E72', marginTop: 4, fontWeight: '600' },
  // Topics
  topicsCard: { backgroundColor: '#fff', borderRadius: 20, padding: 20, marginBottom: 20 },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: '#2D3436', marginBottom: 14 },
  topicsList: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  topicChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16 },
  topicText: { fontSize: 14, fontWeight: '700', textTransform: 'capitalize' },
  // Conversations
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
  // Action button
  actionButton: { borderRadius: 20, overflow: 'hidden', shadowColor: '#4ECDC4', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.35, shadowRadius: 16, elevation: 8 },
  actionGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 18, gap: 10 },
  actionText: { color: '#fff', fontSize: 18, fontWeight: '700' },
  // Conversation detail
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
