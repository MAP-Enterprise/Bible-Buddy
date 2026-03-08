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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { BibleVerseCard } from '../src/components/BibleVerseCard';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const { width } = Dimensions.get('window');

const AGE_TIERS = [
  { value: '4-6', label: '4-6 yrs' },
  { value: '7-9', label: '7-9 yrs' },
  { value: '10-12', label: '10-12 yrs' },
  { value: '13-18', label: '13-18 yrs' },
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
  const [currentSound, setCurrentSound] = useState<Audio.Sound | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  
  const scrollViewRef = useRef<ScrollView>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const bounceAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    loadSettings();
    startBounceAnimation();
    return () => {
      if (currentSound) currentSound.unloadAsync();
    };
  }, []);

  const loadSettings = async () => {
    try {
      const savedAgeTier = await AsyncStorage.getItem('ageTier');
      const savedChildId = await AsyncStorage.getItem('childId');
      if (savedAgeTier) setAgeTier(savedAgeTier);
      if (savedChildId) setChildId(savedChildId);
    } catch (error) {
      console.log('Settings load error:', error);
    }
  };

  const saveSettings = async (key: string, value: string) => {
    try {
      await AsyncStorage.setItem(key, value);
    } catch (error) {
      console.log('Settings save error:', error);
    }
  };

  const startBounceAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(bounceAnim, { toValue: -10, duration: 1000, useNativeDriver: true }),
        Animated.timing(bounceAnim, { toValue: 0, duration: 1000, useNativeDriver: true }),
      ])
    ).start();
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

        // Auto-play audio or use TTS
        if (data.audio_url) {
          playAudio(data.audio_url);
        } else {
          speakText(data.response);
        }
      } else {
        throw new Error('Failed to get response');
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: `msg_${Date.now()}_error`,
        role: 'assistant',
        content: "Oops! I'm having a little trouble right now. Can you try asking again?",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }
  };

  const playAudio = async (audioUrl: string) => {
    try {
      if (currentSound) {
        await currentSound.stopAsync();
        await currentSound.unloadAsync();
      }
      setIsPlaying(true);
      const { sound } = await Audio.Sound.createAsync({ uri: audioUrl }, { shouldPlay: true });
      setCurrentSound(sound);
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          setIsPlaying(false);
          sound.unloadAsync();
        }
      });
    } catch (error) {
      console.error('Audio playback error:', error);
      setIsPlaying(false);
      // Fallback to device TTS
      speakText(messages[messages.length - 1]?.content || '');
    }
  };

  const stopAudio = async () => {
    if (currentSound) await currentSound.stopAsync();
    Speech.stop();
    setIsPlaying(false);
  };

  const speakText = (text: string) => {
    setIsPlaying(true);
    Speech.speak(text, {
      language: 'en',
      pitch: 1.1,
      rate: 0.9,
      onDone: () => setIsPlaying(false),
      onError: () => setIsPlaying(false),
    });
  };

  const startRecording = async () => {
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(newRecording);
      setIsRecording(true);
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.2, duration: 500, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
        ])
      ).start();
    } catch (error) {
      console.error('Recording error:', error);
    }
  };

  const stopRecording = async () => {
    if (!recording) return;
    try {
      setIsRecording(false);
      pulseAnim.stopAnimation();
      pulseAnim.setValue(1);
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      
      if (uri) {
        // For now, show a message that voice is recorded
        // Full voice transcription requires native build
        sendMessage("[Voice message recorded - transcription coming soon!]");
      }
    } catch (error) {
      console.error('Stop recording error:', error);
    }
  };

  const renderMessage = (message: Message) => {
    const isUser = message.role === 'user';
    return (
      <View key={message.id} style={[styles.messageBubble, isUser ? styles.userBubble : styles.assistantBubble]}>
        {!isUser && (
          <View style={styles.avatarContainer}>
            <Text style={styles.avatar}>📖</Text>
          </View>
        )}
        <View style={[styles.messageContent, isUser ? styles.userContent : styles.assistantContent]}>
          <Text style={[styles.messageText, isUser ? styles.userText : styles.assistantText]}>
            {message.content}
          </Text>
          {!isUser && message.bibleVerses && message.bibleVerses.length > 0 && (
            <View style={styles.versesContainer}>
              {message.bibleVerses.map((verse, i) => (
                <BibleVerseCard key={i} verse={verse} />
              ))}
            </View>
          )}
          {!isUser && message.fromKnowledgeBase && (
            <View style={styles.instantBadge}>
              <Ionicons name="flash" size={12} color="#4A90D9" />
              <Text style={styles.instantText}>Instant Answer</Text>
            </View>
          )}
          {!isUser && (
            <TouchableOpacity
              style={styles.audioButton}
              onPress={() => isPlaying ? stopAudio() : speakText(message.content)}
            >
              <Ionicons name={isPlaying ? 'stop-circle' : 'play-circle'} size={24} color="#4A90D9" />
              <Text style={styles.audioButtonText}>{isPlaying ? 'Stop' : 'Listen'}</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    );
  };

  const renderWelcomeScreen = () => (
    <View style={styles.welcomeContainer}>
      <Animated.View style={[styles.logoContainer, { transform: [{ translateY: bounceAnim }] }]}>
        <Text style={styles.logoEmoji}>📖</Text>
        <Text style={styles.logoText}>Bible Buddy</Text>
      </Animated.View>
      <Text style={styles.welcomeText}>Hi there! Ask me anything about God, Jesus, or the Bible!</Text>
      <View style={styles.suggestionContainer}>
        <Text style={styles.suggestionTitle}>Try asking:</Text>
        {['Who made the world?', 'Tell me about Jesus', 'How can I pray?', 'Why does God love me?'].map((suggestion, i) => (
          <TouchableOpacity key={i} style={styles.suggestionButton} onPress={() => sendMessage(suggestion)}>
            <Text style={styles.suggestionText}>{suggestion}</Text>
            <Ionicons name="arrow-forward-circle" size={20} color="#4A90D9" />
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#4A90D9" />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>Bible Buddy</Text>
          <TouchableOpacity onPress={() => setShowSettings(!showSettings)}>
            <Text style={styles.ageTierBadge}>{AGE_TIERS.find(t => t.value === ageTier)?.label}</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity onPress={() => setShowSettings(!showSettings)}>
          <Ionicons name="settings-outline" size={24} color="#4A90D9" />
        </TouchableOpacity>
      </View>

      {/* Settings Panel */}
      {showSettings && (
        <View style={styles.settingsPanel}>
          <Text style={styles.settingsLabel}>Age Group:</Text>
          <View style={styles.ageTierRow}>
            {AGE_TIERS.map((tier) => (
              <TouchableOpacity
                key={tier.value}
                style={[styles.ageTierButton, ageTier === tier.value && styles.ageTierButtonActive]}
                onPress={() => { setAgeTier(tier.value); saveSettings('ageTier', tier.value); }}
              >
                <Text style={[styles.ageTierButtonText, ageTier === tier.value && styles.ageTierButtonTextActive]}>
                  {tier.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity style={styles.newChatButton} onPress={() => { setMessages([]); setSessionId(null); setShowSettings(false); }}>
            <Ionicons name="refresh" size={18} color="#fff" />
            <Text style={styles.newChatButtonText}>New Chat</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Chat Area */}
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.chatContainer}>
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.length === 0 ? renderWelcomeScreen() : (
            <>
              {messages.map(renderMessage)}
              {isLoading && (
                <View style={styles.typingIndicator}>
                  <Text style={styles.typingEmoji}>📖</Text>
                  <ActivityIndicator size="small" color="#4A90D9" />
                  <Text style={styles.typingText}>Thinking...</Text>
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
              onSubmitEditing={() => sendMessage(inputText)}
            />
            <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
              <TouchableOpacity
                style={[styles.voiceButton, isRecording && styles.voiceButtonActive]}
                onPress={isRecording ? stopRecording : startRecording}
              >
                <Ionicons name={isRecording ? 'stop' : 'mic'} size={22} color={isRecording ? '#fff' : '#4A90D9'} />
              </TouchableOpacity>
            </Animated.View>
          </View>
          <TouchableOpacity
            style={[styles.sendButton, (!inputText.trim() || isLoading) && styles.sendButtonDisabled]}
            onPress={() => sendMessage(inputText)}
            disabled={!inputText.trim() || isLoading}
          >
            <Ionicons name="send" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {isPlaying && (
        <View style={styles.playingIndicator}>
          <Ionicons name="volume-high" size={18} color="#4A90D9" />
          <Text style={styles.playingText}>Speaking...</Text>
          <TouchableOpacity onPress={stopAudio}>
            <Ionicons name="close-circle" size={22} color="#666" />
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0F7FF' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#E8F0FE' },
  backButton: { padding: 4 },
  headerCenter: { alignItems: 'center' },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#2C3E50' },
  ageTierBadge: { fontSize: 12, color: '#4A90D9', marginTop: 2 },
  settingsPanel: { backgroundColor: '#fff', padding: 16, borderBottomWidth: 1, borderBottomColor: '#E8F0FE' },
  settingsLabel: { fontSize: 14, fontWeight: '600', color: '#666', marginBottom: 8 },
  ageTierRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  ageTierButton: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, backgroundColor: '#F0F7FF' },
  ageTierButtonActive: { backgroundColor: '#4A90D9' },
  ageTierButtonText: { fontSize: 13, color: '#666' },
  ageTierButtonTextActive: { color: '#fff', fontWeight: '600' },
  newChatButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#4A90D9', paddingVertical: 10, borderRadius: 10, marginTop: 12 },
  newChatButtonText: { color: '#fff', fontWeight: '600', marginLeft: 6 },
  chatContainer: { flex: 1 },
  messagesContainer: { flex: 1 },
  messagesContent: { padding: 16 },
  welcomeContainer: { alignItems: 'center', paddingVertical: 30 },
  logoContainer: { alignItems: 'center', marginBottom: 16 },
  logoEmoji: { fontSize: 64 },
  logoText: { fontSize: 28, fontWeight: '700', color: '#4A90D9' },
  welcomeText: { fontSize: 16, textAlign: 'center', color: '#555', marginBottom: 24 },
  suggestionContainer: { width: '100%' },
  suggestionTitle: { fontSize: 14, fontWeight: '600', color: '#666', marginBottom: 10, textAlign: 'center' },
  suggestionButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#fff', paddingHorizontal: 16, paddingVertical: 14, borderRadius: 12, marginBottom: 8 },
  suggestionText: { fontSize: 15, color: '#333' },
  messageBubble: { flexDirection: 'row', marginBottom: 16, maxWidth: '85%' },
  userBubble: { alignSelf: 'flex-end', flexDirection: 'row-reverse' },
  assistantBubble: { alignSelf: 'flex-start' },
  avatarContainer: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#E8F0FE', alignItems: 'center', justifyContent: 'center', marginRight: 8 },
  avatar: { fontSize: 20 },
  messageContent: { borderRadius: 18, padding: 12, maxWidth: width * 0.7 },
  userContent: { backgroundColor: '#4A90D9', borderBottomRightRadius: 4 },
  assistantContent: { backgroundColor: '#fff', borderBottomLeftRadius: 4 },
  messageText: { fontSize: 15, lineHeight: 21 },
  userText: { color: '#fff' },
  assistantText: { color: '#333' },
  versesContainer: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 8 },
  instantBadge: { flexDirection: 'row', alignItems: 'center', marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#E8F0FE' },
  instantText: { fontSize: 11, color: '#4A90D9', marginLeft: 4 },
  audioButton: { flexDirection: 'row', alignItems: 'center', marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#E8F0FE' },
  audioButtonText: { marginLeft: 4, fontSize: 13, color: '#4A90D9' },
  typingIndicator: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', padding: 12, borderRadius: 18, alignSelf: 'flex-start' },
  typingEmoji: { fontSize: 20, marginRight: 8 },
  typingText: { marginLeft: 8, fontSize: 13, color: '#666' },
  inputContainer: { flexDirection: 'row', alignItems: 'flex-end', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: '#E8F0FE' },
  inputWrapper: { flex: 1, flexDirection: 'row', alignItems: 'flex-end', backgroundColor: '#F8FAFC', borderRadius: 24, paddingHorizontal: 14, paddingVertical: 8, marginRight: 10 },
  textInput: { flex: 1, fontSize: 15, color: '#333', maxHeight: 100, paddingVertical: 6 },
  voiceButton: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#E8F0FE', alignItems: 'center', justifyContent: 'center', marginLeft: 8 },
  voiceButtonActive: { backgroundColor: '#E74C3C' },
  sendButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#4A90D9', alignItems: 'center', justifyContent: 'center' },
  sendButtonDisabled: { backgroundColor: '#B8D4F0' },
  playingIndicator: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#E8F0FE', paddingVertical: 8, gap: 8 },
  playingText: { fontSize: 13, color: '#4A90D9' },
});
