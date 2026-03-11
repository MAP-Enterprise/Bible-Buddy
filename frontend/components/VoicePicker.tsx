import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface VoiceOption {
  id: string;
  name: string;
  gender: string;
  accent: string;
  description: string;
}

interface VoicePickerProps {
  selectedVoiceId: string;
  onSelect: (voiceId: string) => void;
}

export default function VoicePicker({ selectedVoiceId, onSelect }: VoicePickerProps) {
  const [voices, setVoices] = useState<VoiceOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [previewing, setPreviewing] = useState<string | null>(null);

  useEffect(() => {
    fetchVoices();
  }, []);

  const fetchVoices = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/voices`);
      if (res.ok) {
        const data = await res.json();
        setVoices(data.voices || []);
      }
    } catch (e) {
      console.log('Fetch voices error:', e);
    } finally {
      setLoading(false);
    }
  };

  const previewVoice = async (voiceId: string) => {
    setPreviewing(voiceId);
    try {
      const res = await fetch(`${BACKEND_URL}/api/voices/preview?voice_id=${voiceId}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.audio_url) {
          const fullUrl = data.audio_url.startsWith('http') ? data.audio_url : `${BACKEND_URL}${data.audio_url}`;
          const { sound } = await Audio.Sound.createAsync({ uri: fullUrl });
          await sound.playAsync();
          sound.setOnPlaybackStatusUpdate((status: any) => {
            if (status.didJustFinish) {
              sound.unloadAsync();
              setPreviewing(null);
            }
          });
          return;
        }
      }
    } catch (e) {
      console.log('Preview error:', e);
    }
    setPreviewing(null);
  };

  const genderColors: Record<string, { bg: string; text: string; icon: string }> = {
    female: { bg: '#FFE8F0', text: '#E84393', icon: 'woman' },
    male: { bg: '#E8F4FF', text: '#0984E3', icon: 'man' },
  };

  const accentBadgeColors: Record<string, string> = {
    American: '#4ECDC4',
    British: '#6C5CE7',
    African: '#FF6B6B',
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="small" color="#6C5CE7" />
        <Text style={styles.loadingText}>Loading voices...</Text>
      </View>
    );
  }

  const femaleVoices = voices.filter(v => v.gender === 'female');
  const maleVoices = voices.filter(v => v.gender === 'male');

  const renderVoiceCard = (voice: VoiceOption) => {
    const isSelected = selectedVoiceId === voice.id;
    const isPreviewing = previewing === voice.id;
    const genderStyle = genderColors[voice.gender] || genderColors.female;

    return (
      <TouchableOpacity
        key={voice.id}
        style={[styles.voiceCard, isSelected && styles.voiceCardSelected]}
        onPress={() => onSelect(voice.id)}
        activeOpacity={0.8}
        data-testid={`voice-${voice.id}`}
      >
        <View style={styles.voiceCardTop}>
          <View style={[styles.voiceAvatar, { backgroundColor: genderStyle.bg }]}>
            <Ionicons name={genderStyle.icon as any} size={22} color={genderStyle.text} />
          </View>
          <View style={styles.voiceInfo}>
            <Text style={styles.voiceName}>{voice.name}</Text>
            <Text style={styles.voiceDesc}>{voice.description}</Text>
          </View>
          {isSelected && (
            <View style={styles.selectedBadge}>
              <Ionicons name="checkmark-circle" size={24} color="#4ECDC4" />
            </View>
          )}
        </View>
        <View style={styles.voiceCardBottom}>
          <View style={[styles.accentBadge, { backgroundColor: `${accentBadgeColors[voice.accent] || '#999'}18` }]}>
            <Text style={[styles.accentText, { color: accentBadgeColors[voice.accent] || '#999' }]}>{voice.accent}</Text>
          </View>
          <TouchableOpacity
            style={styles.previewButton}
            onPress={() => previewVoice(voice.id)}
            disabled={isPreviewing}
            data-testid={`preview-voice-${voice.id}`}
          >
            {isPreviewing ? (
              <ActivityIndicator size="small" color="#6C5CE7" />
            ) : (
              <>
                <Ionicons name="volume-medium" size={16} color="#6C5CE7" />
                <Text style={styles.previewText}>Preview</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.sectionLabel}>Female Voices</Text>
      {femaleVoices.map(renderVoiceCard)}
      <Text style={[styles.sectionLabel, { marginTop: 16 }]}>Male Voices</Text>
      {maleVoices.map(renderVoiceCard)}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {},
  loadingContainer: { alignItems: 'center', padding: 24, gap: 8 },
  loadingText: { fontSize: 14, color: '#999' },
  sectionLabel: { fontSize: 14, fontWeight: '700', color: '#636E72', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1 },
  voiceCard: { backgroundColor: '#fff', borderRadius: 16, padding: 14, marginBottom: 10, borderWidth: 2, borderColor: '#F0F0F0', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 4, elevation: 1 },
  voiceCardSelected: { borderColor: '#4ECDC4', backgroundColor: '#F0FFFC' },
  voiceCardTop: { flexDirection: 'row', alignItems: 'center' },
  voiceAvatar: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  voiceInfo: { flex: 1 },
  voiceName: { fontSize: 16, fontWeight: '700', color: '#2D3436' },
  voiceDesc: { fontSize: 13, color: '#999', marginTop: 2 },
  selectedBadge: { marginLeft: 8 },
  voiceCardBottom: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 },
  accentBadge: { paddingHorizontal: 12, paddingVertical: 4, borderRadius: 10 },
  accentText: { fontSize: 12, fontWeight: '600' },
  previewButton: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F0ECFF', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12, gap: 4 },
  previewText: { fontSize: 13, fontWeight: '600', color: '#6C5CE7' },
});
