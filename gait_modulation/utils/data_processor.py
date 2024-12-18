import numpy as np
from typing import Dict, Any, Tuple
import mne
import pandas as pd

class DataProcessor:
    @staticmethod
    def process_lfp_data(all_data, n_sessions, lfp_sfreq, event_of_interest, mod_start_event_id, normal_walking_event_id, gap_sample_length, epoch_sample_length, epoch_tmin, epoch_tmax, epoch_duration, event_dict, info, reject_criteria, verbose=False):
        
        lfp_raw_list = []
        epochs_list = []
        events_list = []
        all_lfp_data = []

        for s in range(n_sessions):
            print(f'Session: {s}')
            session = all_data[s]  # Access specific patient/sessions

            # Extract events and lfp data of the subject/session
            lfp_data = session['data_LFP'] #* 1e-6  # Convert microvolts to volts

            # Handle events
            events_KIN = DataProcessor.np_to_dict(session['events_KIN'])
            events_before_trim, event_dict_before_trim = DataProcessor.create_events_array(events_KIN, lfp_sfreq)

            # Trim the data and adjust the event onsets accordingly
            lfp_data, events_after_trim = DataProcessor.trim_data(lfp_data, events_before_trim, lfp_sfreq)
            lfp_duration = lfp_data.shape[1] / lfp_sfreq
            n_samples = int(lfp_duration * lfp_sfreq)

            all_lfp_data.append(lfp_data)

            # Update raw data after trimming
            lfp_raw = mne.io.RawArray(lfp_data, info, verbose=40)
            
            events_mod_start = events_after_trim[events_after_trim[:, 2] == event_dict_before_trim[event_of_interest]]
            events_mod_start[:, 1] = s  # mark the session nr

            # Rename Gait Modulation Events
            events_mod_start[:, 2] = mod_start_event_id

            # Define normal walking events
            normal_walking_events = DataProcessor.define_normal_walking_events(
                normal_walking_event_id, events_mod_start,
                gap_sample_length, epoch_sample_length, n_samples
            )

            events_mod_start[:, 1] = s  # mark the session nr
            normal_walking_events[:, 1] = s  # mark the session nr

            # Combine events and create epochs
            events, epochs = DataProcessor.create_epochs_with_events(
                lfp_raw,
                events_mod_start,
                normal_walking_events,
                mod_start_event_id,
                normal_walking_event_id,
                epoch_tmin,
                epoch_tmax,
                event_dict
            )
            if verbose:
                print(f"Total epochs: {len(epochs)}")
                for cls in event_dict.keys():
                    print(f"{cls}: {len(epochs[cls])} epochs", end='; ')

            epochs.events[:, 1] = s  # mark the session nr
            # Remove bad epochs
            epochs.drop_bad(reject=reject_criteria)
            # my_annot = mne.annotations_from_events(epochs.events, lfp_sfreq)
            my_annot = mne.Annotations(
                onset=(events[:, 0] - epoch_sample_length) / lfp_sfreq,  # in seconds
                duration=len(events) * [epoch_duration],  # in seconds, too
                description=events[:, 2]
            )
            
            lfp_raw.set_annotations(my_annot)
            # lfp_raw.add_events(epochs.events)
            
            lfp_raw_list.append(lfp_raw)         
            
            epochs_list.append(epochs)
            events_list.append(events)
            
            print("\n==========================================================")

        epochs = mne.concatenate_epochs(epochs_list, verbose=40)
        events = np.vstack(events_list)
        events = events[np.argsort(events[:, 0])]  # Sort by onset time
        
        # Generate the channel locations
        ch_locs = DataProcessor.generate_ch_locs(ch_names=lfp_raw.ch_names)
        montage = mne.channels.make_dig_montage(ch_pos=ch_locs)
        epochs.set_montage(montage)

        return epochs, events, lfp_raw_list, all_lfp_data
    
    @staticmethod
    def generate_ch_locs(ch_names):
        ch_locs = {
        'LFP_L03': [-1, -1, -1],
        'LFP_L13': [-1, 0, 0],
        'LFP_L02': [-1, 1, 1],
        'LFP_R03': [1, -1, -1],
        'LFP_R13': [1, 0, 0],
        'LFP_R02': [1, 1, 1]}
        
        # ch_locs = {}
        # for i, ch in enumerate(ch_names):
        #     if 'LFP_L' in ch:
        #         # Example locations for left channels
        #         ch_locs[ch] = [-1, i % 3, i // 3]
        #     elif 'LFP_R' in ch:
        #         # Example locations for right channels
        #         ch_locs[ch] = [1, i % 3, i // 3]
        return ch_locs


    @staticmethod
    def print_data_shapes(data: Dict[str, Any]) -> None:
        """Prints the shapes of the data arrays in the dictionary.

        Args:
            data (Dict[str, Any]): Dictionary 
        """
        for key, value in data.items():
            if value is not None:
                print(f"{key} shape: {value.shape if hasattr(value, 'shape') else 'Not an array'}")
                
    @staticmethod
    def process_events_kin(events_kin: Dict[str, Any]) -> None:
        """Process kinesthetic event data.

        Args:
            events_kin (Dict[str, Any]): Dictionary containing kinesthetic event data.
        """
        if events_kin is None:
            print("No events_KIN data found.")
            return
        labels = events_kin.get('labels', [])
        times = events_kin.get('times', [])
        print(f"Event labels: {labels}")
        print(f"Event times: {times}")
        
    @staticmethod
    def process_events_steps(events_steps: Dict[str, Any]) -> None:
        """Process step event data.

        Args:
            events_steps (Dict[str, Any]): Dictionary containing data
        """
        if events_steps is None:
            print("No events_steps data found.")
            return
        labels = events_steps.get('labels', [])
        times = events_steps.get('times', [])
        print(f"Step event labels: {labels}")
        print(f"Step event times: {times}")
        
      
      
# ------
      
      
    @staticmethod
    def np_to_dict(data_structure: np.ndarray) -> Dict[str, Any]:
        """
        Converts a numpy array-based data structure to a dictionary-like structure.

        Parameters:
        -----------
        data_structure : np.ndarray
            Numpy array-based data structure from which to extract metadata and events.

        Returns:
        --------
        dict
            A dictionary-like structure containing the extracted data from the input numpy array-based structure.
        """
        extracted_data = {n: data_structure[n][0, 0] for n in data_structure.dtype.names}
        return extracted_data
  

    @staticmethod
    def convert_lfp_label(labels: np.ndarray) -> list:
        """
        Convert long-form LFP labels to a more descriptive format.

        Args:
            labels (np.ndarray): Array of long-form LFP labels.

        Returns:
            list: List of converted labels in the format 'LFP_SIDE_DIGITDIGIT', 
                where SIDE is 'L' or 'R', and DIGIT represents the numeric 
                part extracted from each original label.
        """
        text_to_num = {
            'ZERO': '0',
            'ONE': '1',
            'TWO': '2',
            'THREE': '3',
        }
        
        converted_labels = []
        
        for label_array in labels:
            label = label_array[0]  # Extract the label string from the array
            
            # Extracting and printing original label name
            original_label_name = label[0]
            print(f"Original Label Name: {original_label_name}")
            
            parts = original_label_name.split('_')
            if parts[2] == 'LEFT':
                side = 'L'
            else:
                side = 'R'
            
            numeric_part = f"{text_to_num[parts[0]]}{text_to_num[parts[1]]}"
            
            converted_label = f"LFP_{side}{numeric_part}"
            
            # Printing comparison of before and after renaming
            print(f"   Before renaming: {original_label_name}")
            print(f"   After renaming : {converted_label}")
            
            converted_labels.append(converted_label)
        
        return converted_labels

    @staticmethod
    def rename_lfp_channels(labels: np.ndarray) -> list:
        """
        Convert long-form LFP channels to a more descriptive format and ensure uniqueness.

        Args:
            labels (np.ndarray): Array of long-form LFP labels.

        Returns:
            list: List of converted labels in the format 'LFP_SIDE_DIGITDIGIT', 
                where SIDE is 'L' or 'R', and DIGIT represents the numeric 
                part extracted from each original channel.
        """
        text_to_num = {
            'ZERO': '0',
            'ONE': '1',
            'TWO': '2',
            'THREE': '3',
        }
        
        converted_labels = []
        label_count = {}

        for label_array in labels:
            label = label_array[0][0]  # Extract the label string from the array
            parts = label.split('_')
            side = 'L' if parts[2] == 'LEFT' else 'R'
            
            numeric_part = f"{text_to_num[parts[0]]}{text_to_num[parts[1]]}"
            base_label = f"LFP_{side}{numeric_part}"
            
            # Ensure uniqueness by adding a suffix if the label already exists
            if base_label in label_count:
                label_count[base_label] += 1
                unique_label = f"{base_label}_{label_count[base_label]}"
            else:
                label_count[base_label] = 1
                unique_label = base_label
            
            converted_labels.append(unique_label)

        return converted_labels
    
    
    # Vectorized version of create_events_array
    @staticmethod
    def create_events_array(events_kin: Dict[str, Any], sfreq: float) -> Tuple[np.ndarray, Dict[str, int]]:
        """
        Create an MNE-compatible events array from events_KIN data, handling NaN values.

        Parameters:
        -----------
        events_kin : Dict[str, Any]
            Dictionary containing events_KIN data with 'times' and 'label' keys.
        sfreq : float
            Sampling frequency of the LFP data.

        Returns:
        --------
        mne_events : np.ndarray
            MNE-compatible events array (shape: [n_events, 3]).
            Each row contains [sample_index, 0, event_id].
        event_id : Dict[str, int]
            Dictionary mapping event labels to unique event IDs.
        """
        events_kin_times = events_kin['times']
        event_labels = [label[0] for label in events_kin['label'][0]]

        # Map event labels to unique integer IDs
        event_id = {label: idx + 1 for idx, label in enumerate(event_labels)}

        # Handle NaN values in events_kin_times
        valid_mask = ~np.isnan(events_kin_times)
        events_kin_times_valid = events_kin_times[valid_mask]

        # Generate time indices in samples for valid times
        # try:
        time_samples = (events_kin_times_valid * sfreq).astype(int)
        # except TypeError as e:
        #     raise TypeError("Invalid type encountered in events_kin_times or sfreq. Ensure events_kin['times'] is a numeric array and sfreq is a numeric value.") from e
        # except Exception as e:
        #     raise RuntimeError("Error occurred while converting times to samples.") from e

        # Create indices for events and trials based on valid times
        event_indices = np.nonzero(valid_mask)[0]

        # Construct the MNE events array with sample indices
        mne_events = np.column_stack([
            time_samples,
            np.zeros_like(event_indices),
            np.array([event_id[event_labels[event_idx]] for event_idx in event_indices])
        ])

        return mne_events, event_id


    @staticmethod
    def crop_lfp_to_event_times(lfp_data, events_KIN, lfp_sfreq):
        """
        Crop the LFP data to match the time span of the provided event times.
        
        Parameters:
        lfp_data (np.ndarray): 2D array of LFP data with shape (channels, samples).
        events_KIN (dict): Dictionary containing event times.
        lfp_sfreq (float): Sampling frequency of the LFP data.
        
        Returns:
        tuple: Tuple containing:
            - first_non_zero_indices (np.ndarray): Indices of the first non-zero values in each row.
            - cropped_lfp_data (np.ndarray): Cropped LFP data array.
        """
        # Create a mask for non-zero values
        mask = lfp_data != 0
        
        # Find the indices of the first True in each row
        first_non_zero_indices = np.argmax(mask, axis=1)
        
        # Handle rows that have no valid non-zero elements
        valid_rows = mask.any(axis=1)
        first_non_zero_indices[~valid_rows] = -1  # Mark invalid rows with -1
        
        # Index of the first non-zero value across all channels
        max_index = np.max(first_non_zero_indices[valid_rows])
        
        # Map from event time stamp[s] into the sample index of the LFP signals
        ts_session_start = int(events_KIN['times'][0][0] * lfp_sfreq)
        
        try:
            # Crop the LFP signals based on the start and end of the first and last events, respectively.
            ts_session_stop = int(events_KIN['times'][-1][-1] * lfp_sfreq)
            if ts_session_start < ts_session_stop:
                lfp_data = lfp_data[:, ts_session_start:ts_session_stop]
            else:
                print("Session start time is after session stop time. Check the events data.")
        except Exception as e:
            print(f"Error during cropping LFP data: {e}")
        
        return first_non_zero_indices, lfp_data


    def trim_data(
        lfp_data: np.ndarray,
        events: np.ndarray,
        sfreq: float,
        threshold: float = 1e-6
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Trims the beginning of the LFP data by removing leading segments where the signal contains only zero or NaN values,
        and adjusts the events' onsets accordingly. Only trims at the beginning if it contains no signal data.

        Args:
            lfp_data (np.ndarray): 2D array of LFP data with shape (n_channels, n_samples).
            events (np.ndarray): 2D array of events with shape (n_events, 3), where the second column represents onsets.
            sfreq (float): Sampling frequency of the LFP data.
            threshold (float, optional): Value below which the data is considered as "no recorded data". Defaults to 1e-6.

        Returns:
            Tuple[np.ndarray, np.ndarray]: Tuple containing:
                - Trimmed LFP data (2D array with shape (n_channels, trimmed_n_samples)).
                - Adjusted events (2D array with shape (n_events, 3)).

        Prints:
            - Number of samples removed.
            - Number of seconds removed.
            - Number of samples shifted for the onsets.
        """
        # Identify the indices where the data is not NaN or zero
        non_zero_indices = np.any(np.abs(lfp_data) > threshold, axis=0)

        # Find the start index of valid data
        start_index = np.argmax(non_zero_indices)
        
        # If the start index is 0, there is no need to trim
        if start_index == 0:
            print("No trimming needed as the beginning of signal is not flat.")
            return lfp_data, events

        # Trim the LFP data
        trimmed_lfp_data = lfp_data[:, start_index:]

        # Calculate the number of samples removed
        samples_removed = start_index
        seconds_removed = samples_removed / sfreq

        # Adjust the events by shifting the onsets
        adjusted_events = events.copy()
        adjusted_events[:, 0] -= start_index  # Shift event onsets

        # Print the number of samples removed and shifted
        print(f"Number of samples removed: {start_index}")
        print(f"Number of seconds removed: {seconds_removed:.2f} seconds")

        return trimmed_lfp_data, adjusted_events


    def define_normal_walking_events(normal_walking_event_id: int, 
                                    events_mod_start: np.ndarray, 
                                    gap_sample_length: int, 
                                    epoch_sample_length: int, 
                                    n_samples: int) -> np.ndarray:
        """
        Defines normal walking events by creating intervals between modulation events
        and constructing an array of event onsets for normal walking periods.

        Args:
            normal_walking_event_id (int): The event ID assigned to normal walking events.
            events_mod_start (np.ndarray): Array of modulation event start times, where each row
                                        contains the sample onset of a modulation event.
            gap_sample_length (int): Length of the gap in samples to create before and after each modulation event.
            epoch_sample_length (int): The length of the epochs in samples for normal walking events.
            n_samples (int): Total number of samples in the signal.

        Returns:
            np.ndarray: Array containing the normal walking events. Each row contains three values:
                        - The onset of the normal walking event in samples.
                        - A dummy value (always zero).
                        - The event ID (as provided in `normal_walking_event_id`).
        """
        # Calculate gap boundaries (before and after each modulation event)
        gap_boundaries = np.column_stack(
            (events_mod_start[:, 0] - gap_sample_length,
            events_mod_start[:, 0] + gap_sample_length)
        )

        # Construct the output array (normal walking ranges)
        normal_walking_ranges = np.vstack((
            np.array([epoch_sample_length, gap_boundaries[0, 0]]),  # First interval
            np.column_stack((gap_boundaries[:-1, 1], gap_boundaries[1:, 0])),  # Middle intervals
            np.array([gap_boundaries[-1, 1], n_samples])  # Last interval
        ))

        # Ensure no events are generated in gap areas by creating a mask
        mask = normal_walking_ranges[:, 0] <= normal_walking_ranges[:, 1]

        # Apply the mask to filter out invalid ranges
        normal_walking_ranges = normal_walking_ranges[mask]

        # Generate walking onsets by constructing intervals based on epoch_sample_length
        walking_onsets = np.concatenate(
            [np.arange(boundary[0], min(boundary[1], n_samples - epoch_sample_length) + epoch_sample_length, epoch_sample_length)
            for boundary in normal_walking_ranges]
        )

        # Filter out any walking onsets that exceed n_samples
        walking_onsets = walking_onsets[walking_onsets + epoch_sample_length <= n_samples]

        # Create the normal walking event array with the provided event ID
        normal_walking_events = np.column_stack((
            walking_onsets.astype(int),
            np.zeros_like(walking_onsets, dtype=int),
            np.ones_like(walking_onsets, dtype=int) * normal_walking_event_id
        ))

        return normal_walking_events


    
    
    def create_epochs_with_events(lfp_raw: mne.io.Raw, 
                                  events_mod_start: np.ndarray, 
                                  normal_walking_events: np.ndarray, 
                                  gait_modulation_event_id: int, 
                                  normal_walking_event_id: int, 
                                  epoch_tmin: float, 
                                  epoch_tmax: float,
                                  event_dict: Dict[str, int]) -> Tuple[np.ndarray, mne.Epochs]:
        """
        Combines modulation and normal walking events, sorts them by onset time, and creates MNE epochs.

        Args:
            lfp_raw (mne.io.Raw): The raw LFP signal data.
            events_mod_start (np.ndarray): Array of modulation event start times.
            normal_walking_events (np.ndarray): Array of normal walking events.
            gait_modulation_event_id (int): Event ID for gait modulation events.
            normal_walking_event_id (int): Event ID for normal walking events.
            epoch_tmin (float): Start time for epochs (in seconds).
            epoch_tmax (float): End time for epochs (in seconds).
            event_dict (Dict[str, int]): Dictionary mapping event class names to event IDs.
            

        Returns:
            Tuple[np.ndarray, mne.Epochs]: 
                - Array containing the combined and sorted events.
                - The MNE Epochs object containing the epoched data for both modulation and normal walking events.
        """
        # Combine modulation and normal walking events
        events = np.vstack((events_mod_start, normal_walking_events))
        events = events[np.argsort(events[:, 0])]  #TODO Sort events by onset time

        # Create MNE Epochs object
        epochs = mne.Epochs(
            lfp_raw,
            events,
            event_dict,
            tmin=epoch_tmin,
            tmax=epoch_tmax,
            baseline=None,
            preload=True,
            verbose=40
        )

        return events, epochs

    @staticmethod
    def pad_data(trials, max_length, padding_value=0, position="end"):
        """Pad all trials to the specified max_length with the given padding value."""
        padded_trials = []
        for trial in trials:
            pad_size = max(0, max_length - trial.shape[1])  # Calculate required padding based on trial length
            if position == "end":
                padded_trial = np.pad(trial, ((0, 0), (0, pad_size)), mode='constant', constant_values=padding_value)
            else:  # position == "start"
                padded_trial = np.pad(trial, ((0, 0), (pad_size, 0)), mode='constant', constant_values=padding_value)
            padded_trials.append(padded_trial)
        
        return np.array(padded_trials)

    @staticmethod
    def truncate_data(trials, target_length, position="end"):
        """Truncate all trials to the specified target_length."""
        truncated_trials = []
        for trial in trials:
            if trial.shape[1] > target_length:
                if position == "end":
                    truncated_trial = trial[:, :target_length]
                else:  # position == "start"
                    truncated_trial = trial[:, -target_length:]
                truncated_trials.append(truncated_trial)
            else:
                truncated_trials.append(trial)
        
        return np.array(truncated_trials)

    @staticmethod
    def pad_or_truncate(trials, config):
        """Preprocess trials based on padding and truncation settings in config."""
        # Apply padding if enabled
        if config['data_preprocessing']['padding']['enabled']:
            max_length = max([trial.shape[1] for trial in trials])
            trials = DataProcessor.pad_data(
                trials,
                max_length=max_length,
                padding_value=config['data_preprocessing']['padding']['padding_value'],
                position=config['data_preprocessing']['padding']['padding_position']
            )
        
        # Apply truncation if enabled
        if config['data_preprocessing']['truncation']['enabled']:
            target_length = config['data_preprocessing']['truncation']['target_length']            
            if target_length == "min":
                target_length = min([trial.shape[1] for trial in trials])

            trials = DataProcessor.truncate_data(
                trials,
                target_length=target_length,
                position=config['data_preprocessing']['truncation']['truncation_position']
            )
        return trials