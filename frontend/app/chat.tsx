import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Animated,
  ActivityIndicator,
  Dimensions,
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as Speech from 'expo-speech';
import { storage } from '../helpers/storage';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const { width } = Dimensions.get('window');

const AGE_TIERS = [
  { value: '4-6', label: '4-6', color: '#FF6B6B', emoji: '🧒' },
  { value: '7-9', label: '7-9', color: '#4ECDC4', emoji: '👧' },
  { value: '10-12', label: '10-12', color: '#FFD93D', emoji: '🧑' },
  { value: '13-18', label: '13-18', color: '#6C5CE7', emoji: '🎓' },
];

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  audioUrl?: string;
  bibleVerses?: string[];
  fromKnowledgeBase?: boolean;
  timestamp: Date;
}

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [ageTier, setAgeTier] = useState('7-9');
  const [childId, setChildId] = useState('guest_child');
  const [showSettings, setShowSettings] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  
  const scrollViewRef = useRef<ScrollView>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const bounceAnim = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    loadSettings();
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
    Animated.loop(
      Animated.sequence([
        Animated.timing(bounceAnim, { toValue: -8, duration: 1000, useNativeDriver: true }),
        Animated.timing(bounceAnim, { toValue: 0, duration: 1000, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  const loadSettings = async () => {
    try {
      const savedAgeTier = await storage.getItem('ageTier');
      const savedChildId = await storage.getItem('childId');
      if (savedAgeTier) setAgeTier(savedAgeTier);
      if (savedChildId) setChildId(savedChildId);
    } catch (error) {
      console.log('Settings load error:', error);
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          child_id: childId,
          message: text.trim(),
          age_tier: ageTier,
          include_audio: true,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);

        const assistantMessage: Message = {
          id: `msg_${Date.now()}_assistant`,
          role: 'assistant',
          content: data.response,
          audioUrl: data.audio_url,
          bibleVerses: data.bible_verses,
          fromKnowledgeBase: data.from_knowledge_base,
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, assistantMessage]);
        speakText(data.response);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: `msg_${Date.now()}_error`,
        role: 'assistant',
        content: "Oops! Let me try again. Can you ask me once more? 💙",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }
  };

  const speakText = (text: string) => {
    // Check if we're on web and use Web Speech API
    if (Platform.OS === 'web') {
      try {
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
          // Cancel any ongoing speech first
          window.speechSynthesis.cancel();
          
          setIsPlaying(true);
          
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = 'en-US';
          utterance.rate = 0.9;
          utterance.pitch = 1.1;
          utterance.volume = 1;
          
          utterance.onstart = () => {
            console.log('Speech started');
            setIsPlaying(true);
          };
          
          utterance.onend = () => {
            console.log('Speech ended');
            setIsPlaying(false);
          };
          
          utterance.onerror = (event) => {
            console.log('Speech error:', event.error);
            setIsPlaying(false);
          };
          
          // Speak the text
          window.speechSynthesis.speak(utterance);
          console.log('Speech initiated');
        } else {
          console.log('Web Speech API not supported');
          setIsPlaying(false);
        }
      } catch (err) {
        console.log('Speech error:', err);
        setIsPlaying(false);
      }
    } else {
      // Use expo-speech for native platforms
      setIsPlaying(true);
      Speech.speak(text, {
        language: 'en',
        pitch: 1.1,
        rate: 0.9,
        onDone: () => setIsPlaying(false),
        onError: () => setIsPlaying(false),
      });
    }
  };

  const stopAudio = () => {
    if (Platform.OS === 'web') {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    } else {
      Speech.stop();
    }
    setIsPlaying(false);
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    if (!isRecording) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.3, duration: 400, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 400, useNativeDriver: true }),
        ])
      ).start();
      setTimeout(() => {
        setIsRecording(false);
        pulseAnim.stopAnimation();
        pulseAnim.setValue(1);
      }, 3000);
    } else {
      pulseAnim.stopAnimation();
      pulseAnim.setValue(1);
    }
  };

  const currentTier = AGE_TIERS.find(t => t.value === ageTier) || AGE_TIERS[1];

  const renderMessage = (message: Message) => {
    const isUser = message.role === 'user';
    return (
      <Animated.View
        key={message.id}
        style={[styles.messageBubble, isUser ? styles.userBubble : styles.assistantBubble]}
      >
        {!isUser && (
          <LinearGradient colors={['#667eea', '#764ba2']} style={styles.avatarGradient}>
            <Text style={styles.avatarEmoji}>📖</Text>
          </LinearGradient>
        )}
        <View style={[styles.messageContent, isUser ? styles.userContent : styles.assistantContent]}>
          {isUser ? (
            <LinearGradient colors={['#FF6B6B', '#FF8E53']} style={styles.userMessageGradient}>
              <Text style={styles.userText}>{message.content}</Text>
            </LinearGradient>
          ) : (
            <>
              <Text style={styles.assistantText}>{message.content}</Text>
              {message.bibleVerses && message.bibleVerses.length > 0 && (
                <View style={styles.versesContainer}>
                  {message.bibleVerses.map((verse, i) => (
                    <View key={i} style={styles.verseChip}>
                      <Ionicons name="book" size={12} color="#6C5CE7" />
                      <Text style={styles.verseText}>{verse}</Text>
                    </View>
                  ))}
                </View>
              )}
              {message.fromKnowledgeBase && (
                <View style={styles.instantBadge}>
                  <Ionicons name="flash" size={14} color="#FFD93D" />
                  <Text style={styles.instantText}>Instant Answer</Text>
                </View>
              )}
              <TouchableOpacity style={styles.listenButton} onPress={() => isPlaying ? stopAudio() : speakText(message.content)}>
                <Ionicons name={isPlaying ? 'stop-circle' : 'play-circle'} size={26} color="#4ECDC4" />
                <Text style={styles.listenText}>{isPlaying ? 'Stop' : 'Listen'}</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </Animated.View>
    );
  };

  const renderWelcome = () => (
    <Animated.View style={[styles.welcomeContainer, { opacity: fadeAnim }]}>
      <Animated.View style={[styles.welcomeLogo, { transform: [{ translateY: bounceAnim }] }]}>
        <LinearGradient colors={['#667eea', '#764ba2']} style={styles.welcomeLogoGradient}>
          <Text style={styles.welcomeEmoji}>📖</Text>
        </LinearGradient>
        <Text style={styles.welcomeTitle}>Bible Buddy</Text>
        <Text style={styles.welcomeSubtitle}>Ask me anything about God, Jesus, or the Bible!</Text>
      </Animated.View>

      <View style={styles.suggestionsContainer}>
        <Text style={styles.suggestionsTitle}>✨ Try asking:</Text>
        {[
          { text: 'Who made the world?', color: '#FF6B6B', icon: '🌍' },
          { text: 'Tell me about Jesus', color: '#4ECDC4', icon: '✝️' },
          { text: 'How can I pray?', color: '#FFD93D', icon: '🙏' },
          { text: 'Why does God love me?', color: '#6C5CE7', icon: '❤️' },
        ].map((suggestion, i) => (
          <TouchableOpacity
            key={i}
            style={[styles.suggestionCard, { borderLeftColor: suggestion.color }]}
            onPress={() => sendMessage(suggestion.text)}
            activeOpacity={0.7}
          >
            <Text style={styles.suggestionIcon}>{suggestion.icon}</Text>
            <Text style={styles.suggestionText}>{suggestion.text}</Text>
            <View style={[styles.suggestionArrow, { backgroundColor: suggestion.color }]}>
              <Ionicons name="arrow-forward" size={16} color="#fff" />
            </View>
          </TouchableOpacity>
        ))}
      </View>
    </Animated.View>
  );

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Header */}
      <LinearGradient colors={['#667eea', '#764ba2']} style={styles.header}>
        <SafeAreaView edges={['top']} style={styles.headerContent}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <View style={styles.headerCenter}>
            <Text style={styles.headerTitle}>Bible Buddy</Text>
            <TouchableOpacity onPress={() => setShowSettings(!showSettings)} style={styles.ageBadge}>
              <Text style={styles.ageBadgeEmoji}>{currentTier.emoji}</Text>
              <Text style={styles.ageBadgeText}>{currentTier.label} yrs</Text>
            </TouchableOpacity>
          </View>
          <TouchableOpacity onPress={() => setShowSettings(!showSettings)} style={styles.settingsButton}>
            <Ionicons name="settings" size={24} color="#fff" />
          </TouchableOpacity>
        </SafeAreaView>
      </LinearGradient>

      {/* Settings Panel */}
      {showSettings && (
        <Animated.View style={styles.settingsPanel}>
          <Text style={styles.settingsLabel}>🎂 Select Age Group:</Text>
          <View style={styles.ageGrid}>
            {AGE_TIERS.map((tier) => (
              <TouchableOpacity
                key={tier.value}
                style={[
                  styles.ageButton,
                  ageTier === tier.value && { backgroundColor: tier.color },
                ]}
                onPress={() => { setAgeTier(tier.value); storage.setItem('ageTier', tier.value); }}
              >
                <Text style={styles.ageButtonEmoji}>{tier.emoji}</Text>
                <Text style={[styles.ageButtonText, ageTier === tier.value && { color: '#fff' }]}>
                  {tier.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity
            style={styles.newChatButton}
            onPress={() => { setMessages([]); setSessionId(null); setShowSettings(false); }}
          >
            <LinearGradient colors={['#FF6B6B', '#FF8E53']} style={styles.newChatGradient}>
              <Ionicons name="refresh" size={20} color="#fff" />
              <Text style={styles.newChatText}>Start New Chat</Text>
            </LinearGradient>
          </TouchableOpacity>
        </Animated.View>
      )}

      {/* Chat Area */}
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.chatArea}>
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesScroll}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.length === 0 ? renderWelcome() : (
            <>
              {messages.map(renderMessage)}
              {isLoading && (
                <View style={styles.typingContainer}>
                  <LinearGradient colors={['#667eea', '#764ba2']} style={styles.typingAvatar}>
                    <Text style={{ fontSize: 16 }}>📖</Text>
                  </LinearGradient>
                  <View style={styles.typingBubble}>
                    <ActivityIndicator size="small" color="#667eea" />
                    <Text style={styles.typingText}>Thinking...</Text>
                  </View>
                </View>
              )}
            </>
          )}
        </ScrollView>

        {/* Input Area */}
        <View style={styles.inputContainer}>
          <View style={styles.inputWrapper}>
            <TextInput
              style={styles.textInput}
              value={inputText}
              onChangeText={setInputText}
              placeholder="Ask me about the Bible..."
              placeholderTextColor="#999"
              multiline
              maxLength={500}
            />
            <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
              <TouchableOpacity
                style={[styles.micButton, isRecording && styles.micButtonActive]}
                onPress={toggleRecording}
              >
                <Ionicons name={isRecording ? 'stop' : 'mic'} size={22} color={isRecording ? '#fff' : '#6C5CE7'} />
              </TouchableOpacity>
            </Animated.View>
          </View>
          <TouchableOpacity
            style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.sendButtonDisabled]}
            onPress={() => sendMessage(inputText)}
            disabled={!inputText.trim() || isLoading}
          >
            <LinearGradient
              colors={inputText.trim() && !isLoading ? ['#FF6B6B', '#FF8E53'] : ['#DDD', '#CCC']}
              style={styles.sendGradient}
            >
              <Ionicons name="send" size={22} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* Playing Indicator */}
      {isPlaying && (
        <View style={styles.playingBar}>
          <Ionicons name="volume-high" size={20} color="#4ECDC4" />
          <Text style={styles.playingText}>🎵 Bible Buddy is speaking...</Text>
          <TouchableOpacity onPress={stopAudio}>
            <Ionicons name="close-circle" size={24} color="#FF6B6B" />
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FF' },
  header: { paddingBottom: 16 },
  headerContent: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingTop: 8 },
  backButton: { padding: 8 },
  headerCenter: { alignItems: 'center' },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#fff' },
  ageBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, marginTop: 4 },
  ageBadgeEmoji: { fontSize: 14, marginRight: 4 },
  ageBadgeText: { fontSize: 12, color: '#fff', fontWeight: '600' },
  settingsButton: { padding: 8 },
  settingsPanel: { backgroundColor: '#fff', padding: 20, borderBottomLeftRadius: 24, borderBottomRightRadius: 24, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 12, elevation: 8 },
  settingsLabel: { fontSize: 16, fontWeight: '700', color: '#2D3436', marginBottom: 12 },
  ageGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 },
  ageButton: { flex: 1, alignItems: 'center', paddingVertical: 12, marginHorizontal: 4, borderRadius: 16, backgroundColor: '#F8F9FF' },
  ageButtonEmoji: { fontSize: 24, marginBottom: 4 },
  ageButtonText: { fontSize: 13, fontWeight: '600', color: '#636E72' },
  newChatButton: { borderRadius: 14, overflow: 'hidden' },
  newChatGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 14, gap: 8 },
  newChatText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  chatArea: { flex: 1 },
  messagesScroll: { flex: 1 },
  messagesContent: { padding: 16, paddingBottom: 20 },
  welcomeContainer: { alignItems: 'center', paddingVertical: 20 },
  welcomeLogo: { alignItems: 'center', marginBottom: 24 },
  welcomeLogoGradient: { width: 80, height: 80, borderRadius: 40, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  welcomeEmoji: { fontSize: 40 },
  welcomeTitle: { fontSize: 28, fontWeight: '800', color: '#2D3436' },
  welcomeSubtitle: { fontSize: 15, color: '#636E72', marginTop: 6, textAlign: 'center' },
  suggestionsContainer: { width: '100%' },
  suggestionsTitle: { fontSize: 16, fontWeight: '700', color: '#2D3436', marginBottom: 12, textAlign: 'center' },
  suggestionCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 16, borderRadius: 16, marginBottom: 10, borderLeftWidth: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 3 },
  suggestionIcon: { fontSize: 24, marginRight: 12 },
  suggestionText: { flex: 1, fontSize: 15, fontWeight: '600', color: '#2D3436' },
  suggestionArrow: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  messageBubble: { flexDirection: 'row', marginBottom: 16, maxWidth: '88%' },
  userBubble: { alignSelf: 'flex-end', flexDirection: 'row-reverse' },
  assistantBubble: { alignSelf: 'flex-start' },
  avatarGradient: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', marginRight: 10 },
  avatarEmoji: { fontSize: 18 },
  messageContent: { maxWidth: width * 0.72 },
  userContent: { borderRadius: 20, overflow: 'hidden' },
  userMessageGradient: { padding: 14, borderRadius: 20, borderBottomRightRadius: 6 },
  userText: { fontSize: 15, lineHeight: 22, color: '#fff', fontWeight: '500' },
  assistantContent: { backgroundColor: '#fff', borderRadius: 20, borderBottomLeftRadius: 6, padding: 14, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 3 },
  assistantText: { fontSize: 15, lineHeight: 22, color: '#2D3436' },
  versesContainer: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 10, gap: 6 },
  verseChip: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#EDE9FE', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 12, gap: 4 },
  verseText: { fontSize: 12, fontWeight: '600', color: '#6C5CE7' },
  instantBadge: { flexDirection: 'row', alignItems: 'center', marginTop: 10, gap: 4 },
  instantText: { fontSize: 12, fontWeight: '600', color: '#FFD93D' },
  listenButton: { flexDirection: 'row', alignItems: 'center', marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#F0F0F0', gap: 6 },
  listenText: { fontSize: 14, fontWeight: '600', color: '#4ECDC4' },
  typingContainer: { flexDirection: 'row', alignItems: 'center' },
  typingAvatar: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', marginRight: 10 },
  typingBubble: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 12, borderRadius: 18, gap: 8 },
  typingText: { fontSize: 14, color: '#636E72' },
  inputContainer: { flexDirection: 'row', alignItems: 'flex-end', padding: 16, backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: '#F0F0F0' },
  inputWrapper: { flex: 1, flexDirection: 'row', alignItems: 'flex-end', backgroundColor: '#F8F9FF', borderRadius: 24, paddingHorizontal: 16, paddingVertical: 8, marginRight: 10 },
  textInput: { flex: 1, fontSize: 15, color: '#2D3436', maxHeight: 100, paddingVertical: 8 },
  micButton: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#EDE9FE', alignItems: 'center', justifyContent: 'center', marginLeft: 8 },
  micButtonActive: { backgroundColor: '#FF6B6B' },
  sendButton: { borderRadius: 24, overflow: 'hidden' },
  sendButtonDisabled: { opacity: 0.6 },
  sendGradient: { width: 50, height: 50, alignItems: 'center', justifyContent: 'center' },
  playingBar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#E0F7F5', paddingVertical: 10, paddingHorizontal: 20, gap: 10 },
  playingText: { flex: 1, fontSize: 14, fontWeight: '600', color: '#2D3436' },
});
