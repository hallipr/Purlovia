from typing import Any, Dict, Iterator, List, Optional, cast

from ark.types import PrimalGameData
from automate.hierarchy_exporter import ExportModel, Field
from ue.loader import AssetLoadException
from ue.proxy import UEProxyStructure
from ue.utils import get_leaf_from_assetname
from utils.log import get_logger

from .single_asset_stage import SingleAssetExportStage

logger = get_logger(__name__)

__all__ = [
    'ExplorerNotesStage',
]


class AudioEntry(ExportModel):
    waves: List[str]
    transcript: str


class ExplorerNote(ExportModel):
    author: str
    name: str
    authorIcon: Optional[str] = None
    image: Optional[str] = None
    creatureTag: str = Field('None', description="Name tag of a creature this dossier is for.")
    transcript: Optional[str] = None
    audio: Optional[Dict[str, AudioEntry]] = None


EXPLORER_NOTE_TYPE_MAP = {
    0: 'Helena',
    1: 'Rockwell',
    2: 'Mei Yin',
    3: 'Nerva',
    4: 'Bossier',
    6: 'Raia',
    7: 'Dahkeya',
    8: 'Grad Student',
    9: 'Diana',
    10: 'The One Who Waits',
    11: 'Santiago',
    12: 'HLN-A',
    13: 'Nida',
    14: 'Gabriel',
}

GAME_VO_LANGUAGES = ('en', 'de', 'es', 'fe', 'it', 'jp', 'pt', 'ru', 'zh')
GAME_VO_FOLDERS = ('English', 'German', 'Spanish', 'French', 'Italian', 'Japanese', 'Portuguese', 'Russian', 'Mandarin')


class ExplorerNotesStage(SingleAssetExportStage):
    def get_name(self) -> str:
        return 'explorer_notes'

    def get_asset_name(self) -> str:
        '''Return the fullname of the asset to load.'''
        return '/Game/PrimalEarth/CoreBlueprints/COREMEDIA_PrimalGameData_BP'

    def get_use_pretty(self) -> bool:
        return bool(self.manager.config.export_wiki.PrettyJson)

    def get_format_version(self):
        return "1"

    def extract(self, proxy: UEProxyStructure) -> Optional[Dict[str, Any]]:
        pgd = cast(PrimalGameData, proxy)
        results: List[ExplorerNote] = []

        for entry in pgd.ExplorerNoteEntries[0]:
            d = entry.as_dict()
            type_id = int(d['ExplorerNoteType'])

            # Retrieve the path to the author icon reference.
            icon_ref = d['ExplorerNoteIconMaterial']
            icon = None
            if icon_ref and icon_ref.value and icon_ref.value.value:
                icon = icon_ref.value.value.fullname
            else:
                icon_ref = d['ExplorerNoteIcon']
                if icon_ref and icon_ref.value and icon_ref.value.value:
                    icon = icon_ref.value.value.fullname

            # Retrieve the note's texture path.
            texture_ref = d['ExplorerNoteTexture']
            texture = None
            if texture_ref and texture_ref.values[0]:
                texture = str(texture_ref.values[0])

            # Retrieve text/subtitles.
            audio = d['LocalizedAudio'].values
            text = None
            audio_info = None
            if not audio:
                # Classic text note.
                text = str(d['LocalizedSubtitle'])
            else:
                # Audio note.
                # Retrieve all directly linked sound cue paths.
                cues = dict()
                for struct in audio:
                    s = struct.as_dict()
                    language = str(s['TwoLetterISOLanguageName'])
                    cue = s['LocalizedSoundCue'].values[0].value
                    cues[language] = cue

                # Retrieve all texts from cues.
                transcripts = dict()
                waves = None
                for language, cue in cues.items():
                    result = self._get_transcript_from_cue(cue)
                    waves = list(self._retrieve_wave_paths(cue))
                    transcripts[language] = AudioEntry(waves=waves, transcript=result)

                # Retrieve sound wave paths.
                missing_langs = [(i, x) for i, x in enumerate(GAME_VO_LANGUAGES) if x not in transcripts]
                if missing_langs and waves:
                    if all('/English/' in x for x in waves):
                        # Retrieve all runtime discovered sound cue paths.
                        for index, language in missing_langs:
                            subtitles = []

                            for wave in waves:
                                path = self._guess_localised_wave_path(wave, index)
                                if path:
                                    text = self._get_spoken_text_from_wave(path)
                                    if text:
                                        subtitles.append(text)

                            if subtitles:
                                transcripts[language] = AudioEntry(
                                    waves=waves,
                                    transcript='\n'.join(subtitles),
                                )

                audio_info = transcripts

            results.append(
                ExplorerNote(
                    author=EXPLORER_NOTE_TYPE_MAP.get(type_id, type_id),
                    name=str(d['ExplorerNoteDescription']),
                    authorIcon=icon,
                    image=texture,
                    creatureTag=str(d['DossierTameableDinoNameTag']),
                    transcript=text,
                    audio=audio_info,
                ))

        return dict(notes=results)

    def _get_transcript_from_cue(self, cuename: str):
        asset = self.manager.loader[cuename]
        assert asset.default_export
        subtitles = asset.default_export.properties.get_property('Subtitles', fallback=None)

        synced = []
        for subtitle in subtitles:
            d = subtitle.as_dict()
            synced.append((d['Time'].value, d['Text'].source_string.value))

        synced.sort(key=lambda x: x[0])
        return '\n'.join(x[1] for x in synced)

    def _retrieve_wave_paths(self, cuename: str) -> Iterator[str]:
        asset = self.manager.loader[cuename]

        for export in asset.exports:
            clsname = export.klass.value.fullname
            if clsname == '/Script/Engine.SoundNodeWavePlayer':
                sw = export.properties.get_property('SoundWave', fallback=None)
                if sw:
                    yield sw.value.value.fullname

    def _get_spoken_text_from_wave(self, cuename: str) -> Optional[str]:
        asset = self.manager.loader[cuename]

        # Load the asset.
        export = asset.default_export
        if not export:
            return None

        # Retrieve subtitles.
        subtitles = export.properties.get_property('SpokenText', fallback=None)
        if subtitles:
            return subtitles.value
        return None

    def _guess_localised_wave_path(self, wave: str, language: int) -> Optional[str]:
        base_path = wave[:wave.rindex('/English/')]
        base_name = get_leaf_from_assetname(wave)
        base_name = base_name[:-2]

        sw_path = base_path + '/' + GAME_VO_FOLDERS[language] + '/' + base_name + GAME_VO_LANGUAGES[language]
        try:
            self.manager.loader[sw_path]
            return sw_path
        except AssetLoadException:
            return None


def get_sound_wave_path_from_cue(loader, cue_ref: str) -> Optional[str]:
    # Check if cue reference is valid.
    if not cue_ref:
        return None

    # Load the asset.
    cue_asset = loader[cue_ref]
    cue_export = cue_asset.default_export
    if not cue_export:
        return None

    for export in cue_asset.exports:
        clsname = export.klass.value.fullname
        if clsname == '/Script/Engine.SoundNodeWavePlayer':
            sw = export.properties.get_property('SoundWave', fallback=None)
            if sw:
                return sw.value.value.fullname

    return None


def gather_data_from_sound_wave(loader, ref: str) -> Optional[AudioEntry]:
    # Check if cue reference is valid.
    if not ref:
        return None

    # Load the asset.
    asset = loader[ref]
    export = asset.default_export
    if not export:
        return None

    # Retrieve subtitles.
    subtitles = export.properties.get_property('SpokenText', fallback=None)
    if not subtitles:
        return None

    return AudioEntry(bp=ref, transcript=subtitles.value)
