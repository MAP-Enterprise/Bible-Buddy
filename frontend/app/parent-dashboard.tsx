import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface ChildStats {
  child_id: string;
  child_name: string;
  total_conversations: number;
  total_messages: number;
  most_asked_topics: string[];
  last_active: string | null;
}

interface Conversation {
  id: string;
  messages: Array<{ role: string; content: string; timestamp: string }>;
  created_at: string;
  updated_at: string;
}

export default function ParentDashboardScreen() {
  const [childId, setChildId] = useState<string | null>(null);
  const [childName, setChildName] = useState('');
  const [stats, setStats] = useState<ChildStats | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);

  useEffect(() => {
    loadChildData();
  }, []);

  const loadChildData = async () => {
    try {
      const childData = await AsyncStorage.getItem('currentChild');
      if (childData) {
        const child = JSON.parse(childData);
        setChildId(child.child_id);
        setChildName(child.name);
        await fetchData(child.child_id);
      }
    } catch (error) {
      console.error('Load child data error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchData = async (id: string) => {
    try {
      // Fetch sessions for this child
      const sessionsRes = await fetch(`${BACKEND_URL}/api/sessions/${id}`);
      if (sessionsRes.ok) {
        const sessionsData = await sessionsRes.json();
        setConversations(sessionsData.sessions || []);
        
        // Calculate stats locally
        const sessions = sessionsData.sessions || [];
        const totalMessages = sessions.reduce((acc: number, s: any) => acc + (s.messages?.length || 0), 0);
        const topics: { [key: string]: number } = {};
        sessions.forEach((s: any) => {
          s.messages?.forEach((m: any) => {
            if (m.role === 'user') {
              const content = m.content.toLowerCase();
              ['jesus', 'god', 'bible', 'prayer', 'heaven', 'love'].forEach(topic => {
                if (content.includes(topic)) topics[topic] = (topics[topic] || 0) + 1;
              });
            }
          });
        });
        
        const sortedTopics = Object.entries(topics)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 5)
          .map(([topic]) => topic);
        
        setStats({
          child_id: id,
          child_name: childName,
          total_conversations: sessions.length,
          total_messages: totalMessages,
          most_asked_topics: sortedTopics,
          last_active: sessions[0]?.updated_at || null,
        });
      }
    } catch (error) {
      console.error('Fetch data error:', error);
    }
  };

  const onRefresh = async () => {
    setIsRefreshing(true);
    if (childId) await fetchData(childId);
    setIsRefreshing(false);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#4A90D9" />
        </View>
      </SafeAreaView>
    );
  }

  if (selectedConversation) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => setSelectedConversation(null)}>
            <Ionicons name="arrow-back" size={24} color="#4A90D9" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Conversation</Text>
          <View style={{ width: 24 }} />
        </View>
        <ScrollView style={styles.conversationDetail}>
          <Text style={styles.conversationDate}>
            {formatDate(selectedConversation.created_at)}
          </Text>
          {selectedConversation.messages.map((msg, i) => (
            <View key={i} style={[styles.messageItem, msg.role === 'user' ? styles.userMessage : styles.assistantMessage]}>
              <Text style={styles.messageRole}>{msg.role === 'user' ? childName : 'Bible Buddy'}</Text>
              <Text style={styles.messageContent}>{msg.content}</Text>
            </View>
          ))}
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color="#4A90D9" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Parent Dashboard</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={onRefresh} />}
      >
        {/* Child Info */}
        <View style={styles.childCard}>
          <View style={styles.childAvatar}>
            <Text style={styles.childAvatarText}>{childName?.[0]?.toUpperCase() || '?'}</Text>
          </View>
          <View>
            <Text style={styles.childName}>{childName || 'No Child Profile'}</Text>
            <Text style={styles.childId}>ID: {childId?.slice(0, 12)}...</Text>
          </View>
        </View>

        {/* Stats */}
        {stats && (
          <View style={styles.statsContainer}>
            <Text style={styles.sectionTitle}>Usage Statistics</Text>
            <View style={styles.statsGrid}>
              <View style={styles.statCard}>
                <Ionicons name="chatbubbles" size={24} color="#4A90D9" />
                <Text style={styles.statNumber}>{stats.total_conversations}</Text>
                <Text style={styles.statLabel}>Conversations</Text>
              </View>
              <View style={styles.statCard}>
                <Ionicons name="chatbox" size={24} color="#27AE60" />
                <Text style={styles.statNumber}>{stats.total_messages}</Text>
                <Text style={styles.statLabel}>Messages</Text>
              </View>
            </View>
            
            {stats.most_asked_topics.length > 0 && (
              <View style={styles.topicsContainer}>
                <Text style={styles.topicsTitle}>Most Asked Topics</Text>
                <View style={styles.topicsList}>
                  {stats.most_asked_topics.map((topic, i) => (
                    <View key={i} style={styles.topicChip}>
                      <Text style={styles.topicText}>{topic}</Text>
                    </View>
                  ))}
                </View>
              </View>
            )}
          </View>
        )}

        {/* Conversations */}
        <View style={styles.conversationsContainer}>
          <Text style={styles.sectionTitle}>Recent Conversations</Text>
          {conversations.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="chatbubbles-outline" size={48} color="#ccc" />
              <Text style={styles.emptyText}>No conversations yet</Text>
            </View>
          ) : (
            conversations.slice(0, 10).map((conv) => (
              <TouchableOpacity
                key={conv.id}
                style={styles.conversationCard}
                onPress={() => setSelectedConversation(conv)}
              >
                <View style={styles.conversationInfo}>
                  <Text style={styles.conversationPreview}>
                    {conv.messages?.[0]?.content?.slice(0, 50) || 'Empty conversation'}...
                  </Text>
                  <Text style={styles.conversationTime}>{formatDate(conv.updated_at)}</Text>
                </View>
                <Ionicons name="chevron-forward" size={20} color="#999" />
              </TouchableOpacity>
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F7FF' },
  loadingContainer: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, paddingVertical: 16, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#E8F0FE' },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#2C3E50' },
  content: { flex: 1, padding: 16 },
  childCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 16, borderRadius: 16, marginBottom: 16 },
  childAvatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#4A90D9', alignItems: 'center', justifyContent: 'center', marginRight: 16 },
  childAvatarText: { fontSize: 24, fontWeight: '700', color: '#fff' },
  childName: { fontSize: 20, fontWeight: '600', color: '#333' },
  childId: { fontSize: 12, color: '#888', marginTop: 4 },
  statsContainer: { marginBottom: 20 },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#333', marginBottom: 12 },
  statsGrid: { flexDirection: 'row', gap: 12 },
  statCard: { flex: 1, backgroundColor: '#fff', padding: 16, borderRadius: 16, alignItems: 'center' },
  statNumber: { fontSize: 28, fontWeight: '700', color: '#333', marginTop: 8 },
  statLabel: { fontSize: 13, color: '#888', marginTop: 4 },
  topicsContainer: { backgroundColor: '#fff', padding: 16, borderRadius: 16, marginTop: 12 },
  topicsTitle: { fontSize: 14, fontWeight: '600', color: '#666', marginBottom: 10 },
  topicsList: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  topicChip: { backgroundColor: '#E8F0FE', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16 },
  topicText: { fontSize: 13, color: '#4A90D9', textTransform: 'capitalize' },
  conversationsContainer: { marginBottom: 20 },
  emptyState: { alignItems: 'center', padding: 32 },
  emptyText: { fontSize: 14, color: '#888', marginTop: 12 },
  conversationCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 8 },
  conversationInfo: { flex: 1 },
  conversationPreview: { fontSize: 14, color: '#333' },
  conversationTime: { fontSize: 12, color: '#888', marginTop: 4 },
  conversationDetail: { flex: 1, padding: 16 },
  conversationDate: { fontSize: 14, color: '#888', textAlign: 'center', marginBottom: 16 },
  messageItem: { marginBottom: 12, padding: 12, borderRadius: 12 },
  userMessage: { backgroundColor: '#E8F0FE', alignSelf: 'flex-end', maxWidth: '80%' },
  assistantMessage: { backgroundColor: '#fff', alignSelf: 'flex-start', maxWidth: '80%' },
  messageRole: { fontSize: 12, fontWeight: '600', color: '#666', marginBottom: 4 },
  messageContent: { fontSize: 14, color: '#333', lineHeight: 20 },
});
