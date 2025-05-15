"""Tests for the Claude Vision Adapter."""
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, Mock, call
import concurrent.futures

from PIL import Image, ImageEnhance
import numpy as np

from inklink.adapters.claude_vision_adapter import ClaudeVisionAdapter
from inklink.adapters.handwriting_adapter import HandwritingAdapter
from inklink.config import get_config


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for testing."""
    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.stdout = "Test recognition result"
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        yield mock_run


@pytest.fixture
def mock_os_path_exists():
    """Mock os.path.exists for testing file existence checks."""
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        yield mock_exists


@pytest.fixture
def mock_file_open():
    """Mock file operations."""
    mock_file = MagicMock()
    mock_file.__enter__.return_value.read.return_value = "Test persona content"
    
    with patch("builtins.open", return_value=mock_file):
        yield mock_file


@pytest.fixture
def mock_pil():
    """Mock PIL/Pillow image operations."""
    mock_image = MagicMock(spec=Image.Image)
    mock_image.size = (800, 600)
    mock_image.mode = 'RGB'
    mock_image.convert.return_value = mock_image
    mock_image.filter.return_value = mock_image
    mock_image.resize.return_value = mock_image
    mock_image.point.return_value = mock_image
    mock_image.save.return_value = None
    
    # Mock enhancers
    mock_contrast = MagicMock()
    mock_contrast.enhance.return_value = mock_image
    mock_brightness = MagicMock()
    mock_brightness.enhance.return_value = mock_image
    
    with patch('PIL.Image.open', return_value=mock_image) as mock_open, \
         patch('PIL.ImageEnhance.Contrast', return_value=mock_contrast) as mock_contrast_cls, \
         patch('PIL.ImageEnhance.Brightness', return_value=mock_brightness) as mock_brightness_cls, \
         patch('numpy.mean', return_value=128) as mock_np_mean, \
         patch('numpy.array', return_value=np.array([128])) as mock_np_array:
        
        yield {
            'image': mock_image,
            'open': mock_open,
            'contrast': mock_contrast_cls,
            'brightness': mock_brightness_cls,
            'np_mean': mock_np_mean,
            'np_array': mock_np_array
        }


@pytest.fixture
def claude_vision_adapter(mock_subprocess, mock_os_path_exists, mock_file_open):
    """Create a ClaudeVisionAdapter instance for testing."""
    config = get_config()
    config.CLAUDE_COMMAND = "claude"
    config.CLAUDE_MODEL = "claude-3-haiku-20240307"
    
    # Using the constructor directly with named parameters for more control
    return ClaudeVisionAdapter(
        claude_command=config.CLAUDE_COMMAND,
        model=config.CLAUDE_MODEL,
        enable_preprocessing=True,
        contrast_factor=1.5,
        brightness_factor=1.2,
        target_dpi=300,
        apply_thresholding=True
    )


@pytest.fixture
def claude_vision_adapter_no_preprocessing(mock_subprocess, mock_os_path_exists, mock_file_open):
    """Create a ClaudeVisionAdapter instance with preprocessing disabled."""
    config = get_config()
    config.CLAUDE_COMMAND = "claude"
    config.CLAUDE_MODEL = "claude-3-haiku-20240307"
    
    return ClaudeVisionAdapter(
        claude_command=config.CLAUDE_COMMAND,
        model=config.CLAUDE_MODEL,
        enable_preprocessing=False
    )


@pytest.fixture
def claude_vision_adapter_parallel(mock_subprocess, mock_os_path_exists, mock_file_open):
    """Create a ClaudeVisionAdapter instance with parallel processing enabled."""
    config = get_config()
    config.CLAUDE_COMMAND = "claude"
    config.CLAUDE_MODEL = "claude-3-haiku-20240307"
    
    return ClaudeVisionAdapter(
        claude_command=config.CLAUDE_COMMAND,
        model=config.CLAUDE_MODEL,
        enable_preprocessing=True,
        enable_parallel_processing=True,
        max_parallel_workers=2
    )


@pytest.fixture
def claude_vision_adapter_sequential(mock_subprocess, mock_os_path_exists, mock_file_open):
    """Create a ClaudeVisionAdapter instance with parallel processing disabled."""
    config = get_config()
    config.CLAUDE_COMMAND = "claude"
    config.CLAUDE_MODEL = "claude-3-haiku-20240307"
    
    return ClaudeVisionAdapter(
        claude_command=config.CLAUDE_COMMAND,
        model=config.CLAUDE_MODEL,
        enable_preprocessing=True,
        enable_parallel_processing=False
    )


@pytest.fixture
def handwriting_adapter(claude_vision_adapter):
    """Create a HandwritingAdapter instance for testing."""
    config = get_config()
    
    return HandwritingAdapter(
        config=config,
        handwriting_web_adapter=None,  # Not needed for Claude Vision tests
        claude_vision_adapter=claude_vision_adapter
    )


def test_process_image(claude_vision_adapter, mock_subprocess):
    """Test processing a single image."""
    # Arrange
    image_path = "/tmp/test_image.png"
    
    # Act
    result = claude_vision_adapter.process_image(image_path)
    
    # Assert
    assert result == "Test recognition result"
    mock_subprocess.assert_called_once()
    
    # Verify claude command was called with correct parameters
    args = mock_subprocess.call_args[0][0]
    assert "claude" in args
    assert image_path in args


def test_process_multiple_images(claude_vision_adapter, mock_subprocess):
    """Test processing multiple images."""
    # Arrange
    image_paths = ["/tmp/test_image1.png", "/tmp/test_image2.png"]
    
    # Act
    result = claude_vision_adapter.process_multiple_images(image_paths)
    
    # Assert
    assert result == "Test recognition result"
    mock_subprocess.assert_called_once()
    
    # Verify claude command was called with correct parameters
    args = mock_subprocess.call_args[0][0]
    assert "claude" in args
    for path in image_paths:
        assert path in args


def test_persona_loading(claude_vision_adapter, mock_file_open):
    """Test that the adapter loads the Lilly persona correctly."""
    # Act
    persona = claude_vision_adapter._get_persona_content()
    
    # Assert
    assert persona == "Test persona content"
    mock_file_open.__enter__.return_value.read.assert_called_once()


def test_handwriting_adapter_integration(handwriting_adapter, claude_vision_adapter, mock_subprocess):
    """Test the integration between HandwritingAdapter and ClaudeVisionAdapter."""
    # Arrange
    rm_file_path = "/tmp/test_file.rm"
    rendered_image_path = "/tmp/rendered_image.png"
    
    with patch.object(handwriting_adapter, "render_rm_file", return_value=rendered_image_path):
        # Act
        result = handwriting_adapter.process_rm_file(rm_file_path)
        
        # Assert
        assert result == "Test recognition result"
        # Verify rendering and processing flow
        handwriting_adapter.render_rm_file.assert_called_once_with(rm_file_path)
        # Verify Claude Vision adapter was called with the rendered image
        mock_subprocess.assert_called_once()


def test_multi_page_recognition(handwriting_adapter, claude_vision_adapter, mock_subprocess):
    """Test the multi-page recognition flow."""
    # Arrange
    rm_file_paths = ["/tmp/test_file1.rm", "/tmp/test_file2.rm"]
    rendered_image_paths = ["/tmp/rendered_image1.png", "/tmp/rendered_image2.png"]
    
    # Mock render_rm_file to return different paths for different inputs
    def side_effect(path):
        index = rm_file_paths.index(path)
        return rendered_image_paths[index]
    
    with patch.object(handwriting_adapter, "render_rm_file", side_effect=side_effect):
        # Act
        result = handwriting_adapter.recognize_multi_page_handwriting(rm_file_paths)
        
        # Assert
        assert result == "Test recognition result"
        # Verify each file was rendered
        assert handwriting_adapter.render_rm_file.call_count == len(rm_file_paths)
        # Verify Claude Vision adapter was called with all rendered images
        mock_subprocess.assert_called_once()


def test_preprocess_image_text(claude_vision_adapter, mock_pil, mock_os_path_exists):
    """Test preprocessing functionality for text content."""
    # Arrange
    image_path = "/tmp/test_image.png"
    
    # Act
    result = claude_vision_adapter.preprocess_image(image_path, content_type="text")
    
    # Assert
    assert result == "/tmp/test_image_preprocessed.png"
    mock_pil['open'].assert_called_once_with(image_path)
    mock_pil['contrast'].assert_called_once_with(mock_pil['image'])
    mock_pil['brightness'].assert_called_once_with(mock_pil['image'])
    mock_pil['contrast'].return_value.enhance.assert_called_once_with(claude_vision_adapter.contrast_factor)
    mock_pil['brightness'].return_value.enhance.assert_called_once_with(claude_vision_adapter.brightness_factor)
    # Verify sharpening for text content
    mock_pil['image'].filter.assert_called_once()
    # Verify image was saved
    mock_pil['image'].save.assert_called_once()


def test_preprocess_image_math(claude_vision_adapter, mock_pil, mock_os_path_exists):
    """Test preprocessing functionality for math content."""
    # Arrange
    image_path = "/tmp/test_image.png"
    
    # Act
    result = claude_vision_adapter.preprocess_image(image_path, content_type="math")
    
    # Assert
    assert result == "/tmp/test_image_preprocessed.png"
    mock_pil['open'].assert_called_once_with(image_path)
    mock_pil['contrast'].assert_called_once_with(mock_pil['image'])
    mock_pil['brightness'].assert_called_once_with(mock_pil['image'])
    # Verify contrast is lower for math (0.9 factor)
    mock_pil['contrast'].return_value.enhance.assert_called_once_with(claude_vision_adapter.contrast_factor * 0.9)
    mock_pil['brightness'].return_value.enhance.assert_called_once_with(claude_vision_adapter.brightness_factor)
    # Verify DETAIL filter is used for math content
    mock_pil['image'].filter.assert_called_once()


def test_preprocess_image_diagram(claude_vision_adapter, mock_pil, mock_os_path_exists):
    """Test preprocessing functionality for diagram content."""
    # Arrange
    image_path = "/tmp/test_image.png"
    
    # Act
    result = claude_vision_adapter.preprocess_image(image_path, content_type="diagram")
    
    # Assert
    assert result == "/tmp/test_image_preprocessed.png"
    mock_pil['open'].assert_called_once_with(image_path)
    mock_pil['contrast'].assert_called_once_with(mock_pil['image'])
    # Verify contrast is even lower for diagrams (0.8 factor)
    mock_pil['contrast'].return_value.enhance.assert_called_once_with(claude_vision_adapter.contrast_factor * 0.8)
    # Verify EDGE_ENHANCE filter is used for diagram content
    mock_pil['image'].filter.assert_called_once()


def test_preprocess_image_small_resolution(claude_vision_adapter, mock_pil, mock_os_path_exists):
    """Test preprocessing functionality for small images that need resolution enhancement."""
    # Arrange
    image_path = "/tmp/test_image_small.png"
    # Set a small size to trigger resolution enhancement
    mock_pil['image'].size = (500, 400)
    
    # Act
    result = claude_vision_adapter.preprocess_image(image_path, content_type="text")
    
    # Assert
    assert result == "/tmp/test_image_small_preprocessed.png"
    # Verify resize was called for small image
    mock_pil['image'].resize.assert_called_once()
    # Check resize dimensions based on target DPI
    args, _ = mock_pil['image'].resize.call_args
    width, height = args[0]
    assert width > 500 and height > 400


def test_preprocessing_disabled(claude_vision_adapter_no_preprocessing, mock_pil, mock_os_path_exists):
    """Test that preprocessing is skipped when disabled."""
    # Arrange
    image_path = "/tmp/test_image.png"
    
    # Act
    result = claude_vision_adapter_no_preprocessing.preprocess_image(image_path, content_type="text")
    
    # Assert
    assert result == image_path  # Should return original path when disabled
    # PIL operations should not be called when preprocessing is disabled
    mock_pil['open'].assert_not_called()


def test_preprocess_image_error_handling(claude_vision_adapter, mock_os_path_exists):
    """Test error handling in the preprocessing pipeline."""
    # Arrange
    image_path = "/tmp/test_image.png"
    
    # Setup PIL.Image.open to raise an exception
    with patch('PIL.Image.open', side_effect=Exception("Test error")):
        # Act
        result = claude_vision_adapter.preprocess_image(image_path, content_type="text")
        
        # Assert
        # Should return original path when preprocessing fails
        assert result == image_path


def test_process_image_with_preprocessing(claude_vision_adapter, mock_pil, mock_subprocess, mock_file_open, mock_os_path_exists):
    """Test the full image processing pipeline with preprocessing enabled."""
    # Arrange
    image_path = "/tmp/test_image.png"
    preprocessed_path = "/tmp/test_image_preprocessed.png"
    
    # Mock the preprocess_image method to return a known path
    with patch.object(claude_vision_adapter, 'preprocess_image', return_value=preprocessed_path) as mock_preprocess:
        # Act
        result = claude_vision_adapter.process_image(image_path, content_type="text")
        
        # Assert
        mock_preprocess.assert_called_once_with(image_path, "text")
        mock_subprocess.assert_called_once()
        
        # Verify Claude was called with the preprocessed image path
        args = mock_subprocess.call_args[0][0]
        assert preprocessed_path in args


def test_cleanup_preprocessed_image(claude_vision_adapter, mock_pil, mock_subprocess, mock_file_open, mock_os_path_exists):
    """Test that preprocessed images are cleaned up after processing."""
    # Arrange
    image_path = "/tmp/test_image.png"
    preprocessed_path = "/tmp/test_image_preprocessed.png"
    
    # Mock the preprocess_image method to return a known path
    with patch.object(claude_vision_adapter, 'preprocess_image', return_value=preprocessed_path) as mock_preprocess, \
         patch('os.unlink') as mock_unlink:
        # Act
        result = claude_vision_adapter.process_image(image_path, content_type="text")
        
        # Assert
        # Verify the preprocessed image was cleaned up
        mock_unlink.assert_any_call(preprocessed_path)


def test_override_preprocessing_setting(claude_vision_adapter, mock_pil, mock_os_path_exists):
    """Test that the preprocess parameter overrides the class setting."""
    # Arrange
    image_path = "/tmp/test_image.png"
    
    # Mock preprocess_image to track calls
    with patch.object(claude_vision_adapter, 'preprocess_image', return_value=image_path) as mock_preprocess:
        # Act - Force preprocessing off even though the adapter has it enabled
        claude_vision_adapter.process_image(image_path, content_type="text", preprocess=False)
        
        # Assert
        mock_preprocess.assert_not_called()
        
        # Act - Force preprocessing on with explicit parameter
        claude_vision_adapter.process_image(image_path, content_type="text", preprocess=True)
        
        # Assert
        mock_preprocess.assert_called_once()


def test_detect_content_type_text(claude_vision_adapter, mock_pil, mock_os_path_exists):
    """Test content type detection for text."""
    # Arrange
    image_path = "/tmp/test_image_text.png"
    
    # Configure mock for text detection
    mock_edge_img = MagicMock()
    mock_edge_array = MagicMock()
    mock_pil['image'].filter.return_value = mock_edge_img
    mock_edge_img.convert.return_value = mock_edge_img
    
    # Set up edge density for text (low density)
    with patch('numpy.array', return_value=np.array([50])) as mock_np_array, \
         patch('numpy.mean', return_value=0.05) as mock_np_mean:  # 5% edge density, below 10% threshold
        
        # Act
        result = claude_vision_adapter.detect_content_type(image_path)
        
        # Assert
        assert result == "text"
        mock_pil['open'].assert_called_once_with(image_path)
        mock_pil['image'].filter.assert_called_once()  # Called for edge detection


def test_detect_content_type_diagram(claude_vision_adapter, mock_pil, mock_os_path_exists):
    """Test content type detection for diagram."""
    # Arrange
    image_path = "/tmp/test_image_diagram.png"
    
    # Configure mock for diagram detection
    mock_edge_img = MagicMock()
    mock_edge_array = MagicMock()
    mock_pil['image'].filter.return_value = mock_edge_img
    mock_edge_img.convert.return_value = mock_edge_img
    
    # Set up edge density for diagram (high density)
    with patch('numpy.array', return_value=np.array([150])) as mock_np_array, \
         patch('numpy.mean', return_value=0.15) as mock_np_mean:  # 15% edge density, above 10% threshold
        
        # Act
        result = claude_vision_adapter.detect_content_type(image_path)
        
        # Assert
        assert result == "diagram"
        mock_pil['open'].assert_called_once_with(image_path)
        mock_pil['image'].filter.assert_called_once()  # Called for edge detection


def test_detect_content_type_error(claude_vision_adapter, mock_os_path_exists):
    """Test error handling in content type detection."""
    # Arrange
    image_path = "/tmp/test_image.png"
    
    # Setup PIL.Image.open to raise an exception
    with patch('PIL.Image.open', side_effect=Exception("Test error")):
        # Act
        result = claude_vision_adapter.detect_content_type(image_path)
        
        # Assert
        # Should default to "text" on error
        assert result == "text"


def test_process_single_image_for_batch(claude_vision_adapter, mock_subprocess, mock_file_open, mock_os_path_exists):
    """Test processing a single image as part of a batch."""
    # Arrange
    image_path = "/tmp/test_image.png"
    page_index = 1
    total_pages = 3
    content_type = "text"
    context = "Previous page content for context"
    
    # Mock process_image to return a successful result
    with patch.object(claude_vision_adapter, 'process_image', return_value=(True, "Recognized text")) as mock_process:
        # Act
        success, result = claude_vision_adapter._process_single_image_for_batch(
            image_path=image_path,
            page_index=page_index,
            total_pages=total_pages,
            content_type=content_type,
            context=context
        )
        
        # Assert
        assert success is True
        assert "--- PAGE 2 ---" in result  # Page index + 1
        assert "Recognized text" in result
        
        # Verify process_image was called with correct parameters
        mock_process.assert_called_once()
        args, kwargs = mock_process.call_args
        assert kwargs["image_path"] == image_path
        assert kwargs["content_type"] == content_type
        assert "page (2 of 3)" in kwargs["prompt"]  # Page numbers in prompt
        assert context in kwargs["prompt"]  # Context included in prompt


def test_process_single_image_for_batch_content_detection(claude_vision_adapter, mock_subprocess, mock_file_open, mock_os_path_exists):
    """Test content type detection when processing a batch image."""
    # Arrange
    image_path = "/tmp/test_image.png"
    
    # Mock detect_content_type and process_image
    with patch.object(claude_vision_adapter, 'detect_content_type', return_value="diagram") as mock_detect, \
         patch.object(claude_vision_adapter, 'process_image', return_value=(True, "Recognized diagram")) as mock_process:
        
        # Act - without specifying content_type
        claude_vision_adapter._process_single_image_for_batch(
            image_path=image_path,
            page_index=0,
            total_pages=1
        )
        
        # Assert
        mock_detect.assert_called_once_with(image_path)
        mock_process.assert_called_once()
        # Verify detected content type was used
        assert mock_process.call_args[1]["content_type"] == "diagram"


def test_parallel_process_multiple_images(claude_vision_adapter_parallel, mock_subprocess, mock_file_open, mock_os_path_exists):
    """Test parallel processing of multiple images."""
    # Arrange
    image_paths = ["/tmp/test_image1.png", "/tmp/test_image2.png", "/tmp/test_image3.png"]
    
    # Mock ThreadPoolExecutor and futures for parallel processing
    mock_future1 = MagicMock()
    mock_future1.result.return_value = (True, "--- PAGE 1 ---\nPage 1 content\n")
    
    mock_future2 = MagicMock()
    mock_future2.result.return_value = (True, "--- PAGE 2 ---\nPage 2 content\n")
    
    mock_future3 = MagicMock()
    mock_future3.result.return_value = (True, "--- PAGE 3 ---\nPage 3 content\n")
    
    # Setup executor mock
    mock_executor = MagicMock()
    mock_executor.__enter__.return_value.submit.side_effect = [mock_future1, mock_future2, mock_future3]
    
    # Mock _process_single_image_for_batch to avoid actually calling it
    with patch('concurrent.futures.ThreadPoolExecutor', return_value=mock_executor) as mock_pool, \
         patch.object(claude_vision_adapter_parallel, '_process_single_image_for_batch') as mock_process_single, \
         patch('concurrent.futures.as_completed', return_value=[mock_future1, mock_future2, mock_future3]):
        
        # Act
        success, result = claude_vision_adapter_parallel.process_multiple_images(
            image_paths=image_paths,
            maintain_context=False,  # Don't maintain context to use parallel processing
            use_parallel=True
        )
        
        # Assert
        assert success is True
        assert "Page 1 content" in result
        assert "Page 2 content" in result
        assert "Page 3 content" in result
        
        # Verify ThreadPoolExecutor was called with max_workers
        mock_pool.assert_called_once_with(max_workers=2)  # From fixture
        
        # Verify submit was called for each image
        assert mock_executor.__enter__.return_value.submit.call_count == 3


def test_sequential_with_context_process_multiple_images(claude_vision_adapter_sequential, mock_os_path_exists):
    """Test sequential processing with context preservation between pages."""
    # Arrange
    image_paths = ["/tmp/test_image1.png", "/tmp/test_image2.png"]
    
    # Mock _process_single_image_for_batch to return page content
    side_effects = [
        (True, "--- PAGE 1 ---\nFirst page content\n"),
        (True, "--- PAGE 2 ---\nSecond page with context from first\n")
    ]
    
    with patch.object(claude_vision_adapter_sequential, '_process_single_image_for_batch', side_effect=side_effects) as mock_process:
        # Act
        success, result = claude_vision_adapter_sequential.process_multiple_images(
            image_paths=image_paths,
            maintain_context=True  # Enable context preservation
        )
        
        # Assert
        assert success is True
        assert "First page content" in result
        assert "Second page with context from first" in result
        
        # Verify process was called for each page with the right parameters
        assert mock_process.call_count == 2
        
        # First page should be called without context
        first_call_args = mock_process.call_args_list[0][1]
        assert first_call_args["image_path"] == image_paths[0]
        assert first_call_args["page_index"] == 0
        assert first_call_args["context"] is None
        
        # Second page should be called with context from first page
        second_call_args = mock_process.call_args_list[1][1]
        assert second_call_args["image_path"] == image_paths[1]
        assert second_call_args["page_index"] == 1
        assert second_call_args["context"] is not None
        assert "First page content" in second_call_args["context"]


def test_process_multiple_images_error_handling(claude_vision_adapter_sequential, mock_os_path_exists):
    """Test error handling in multi-page processing."""
    # Arrange
    image_paths = ["/tmp/test_image1.png", "/tmp/test_image2.png", "/tmp/test_image3.png"]
    
    # Mock _process_single_image_for_batch to succeed for some pages and fail for others
    side_effects = [
        (True, "--- PAGE 1 ---\nFirst page content\n"),
        (False, "Failed to process page 2"),
        (True, "--- PAGE 3 ---\nThird page content\n")
    ]
    
    with patch.object(claude_vision_adapter_sequential, '_process_single_image_for_batch', side_effect=side_effects) as mock_process:
        # Act - without maintain_context to test partial success
        success, result = claude_vision_adapter_sequential.process_multiple_images(
            image_paths=image_paths,
            maintain_context=False
        )
        
        # Assert
        assert success is True  # Should succeed even with partial failure
        assert "First page content" in result
        assert "Third page content" in result
        assert mock_process.call_count == 3


def test_process_multiple_images_partial_success_rate(claude_vision_adapter_sequential, mock_os_path_exists):
    """Test success rate calculation for multi-page processing."""
    # Arrange
    image_paths = ["/tmp/test_image1.png", "/tmp/test_image2.png", "/tmp/test_image3.png", "/tmp/test_image4.png"]
    
    # Mock _process_single_image_for_batch to succeed for half the pages
    side_effects = [
        (True, "--- PAGE 1 ---\nFirst page content\n"),
        (False, "Failed to process page 2"),
        (True, "--- PAGE 3 ---\nThird page content\n"),
        (False, "Failed to process page 4")
    ]
    
    with patch.object(claude_vision_adapter_sequential, '_process_single_image_for_batch', side_effect=side_effects) as mock_process, \
         patch.object(claude_vision_adapter_sequential, 'logger') as mock_logger:
        
        # Act
        success, result = claude_vision_adapter_sequential.process_multiple_images(
            image_paths=image_paths,
            maintain_context=False  # Disable context to test partial success
        )
        
        # Assert
        assert success is True  # Should return success even with partial failures
        assert "First page content" in result
        assert "Third page content" in result
        
        # Verify success rate logging (2 out of 4 = 50%)
        mock_logger.warning.assert_called_once()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "Partial success" in warning_msg
        assert "2/4" in warning_msg
        assert "50" in warning_msg  # 50% success rate


def test_parallel_processing_with_retries(claude_vision_adapter_parallel, mock_os_path_exists):
    """Test retry mechanism in parallel processing."""
    # Arrange
    image_paths = ["/tmp/test_image1.png", "/tmp/test_image2.png"]
    
    # Create a mock process_image that fails on first call for the second image but succeeds on retry
    process_call_count = {}
    
    def mock_process_with_retry(image_path, **kwargs):
        if image_path not in process_call_count:
            process_call_count[image_path] = 0
        
        process_call_count[image_path] += 1
        
        # First image always succeeds
        if image_path == image_paths[0]:
            return True, "Page 1 content"
            
        # Second image fails on first attempt, succeeds on second
        if image_path == image_paths[1]:
            if process_call_count[image_path] == 1:
                return False, "Temporary failure"
            else:
                return True, "Page 2 content after retry"
    
    # Setup the test environment
    with patch.object(claude_vision_adapter_parallel, 'process_image', side_effect=mock_process_with_retry) as mock_process, \
         patch.object(claude_vision_adapter_parallel, 'detect_content_type', return_value="text"), \
         patch.object(claude_vision_adapter_parallel, 'logger'), \
         patch.object(claude_vision_adapter_parallel, 'safe_process_with_retries', wraps=claude_vision_adapter_parallel.safe_process_with_retries) as mock_safe_process:
            
            # Act
            success, result = claude_vision_adapter_parallel.process_multiple_images(
                image_paths=image_paths,
                maintain_context=False,  # Disable context for parallel processing
                content_types=["text", "text"]  # Explicitly set content types
            )
            
            # Assert
            assert success is True
            assert process_call_count[image_paths[1]] > 1  # Verify second image was retried
            assert "Page 1 content" in result
            assert "Page 2 content after retry" in result


def test_concurrent_error_handling(claude_vision_adapter_parallel, mock_os_path_exists):
    """Test error handling during parallel execution."""
    # Arrange
    image_paths = ["/tmp/test_image1.png", "/tmp/test_image2.png", "/tmp/test_image3.png"]
    
    # Mock futures with different results
    mock_future1 = MagicMock()
    mock_future1.result.return_value = (True, "--- PAGE 1 ---\nPage 1 content\n")
    
    # Future 2 raises an exception when result() is called
    mock_future2 = MagicMock()
    mock_future2.result.side_effect = Exception("Error in thread processing")
    
    mock_future3 = MagicMock()
    mock_future3.result.return_value = (True, "--- PAGE 3 ---\nPage 3 content\n")
    
    # Setup executor mock
    mock_executor = MagicMock()
    mock_executor.__enter__.return_value.submit.side_effect = [mock_future1, mock_future2, mock_future3]
    
    # Setup logger mock
    with patch('concurrent.futures.ThreadPoolExecutor', return_value=mock_executor) as mock_pool, \
         patch.object(claude_vision_adapter_parallel, '_process_single_image_for_batch') as mock_process, \
         patch('concurrent.futures.as_completed', return_value=[mock_future1, mock_future2, mock_future3]), \
         patch.object(claude_vision_adapter_parallel, 'logger') as mock_logger:
        
        # Act
        success, result = claude_vision_adapter_parallel.process_multiple_images(
            image_paths=image_paths,
            maintain_context=False,
            use_parallel=True
        )
        
        # Assert
        assert success is True  # Should still succeed with partial results
        assert "Page 1 content" in result
        assert "Page 3 content" in result
        
        # Verify error was logged
        mock_logger.error.assert_any_call(f"Error processing page 2: Error in thread processing")


def test_mixed_content_types_batch(claude_vision_adapter_sequential, mock_os_path_exists):
    """Test processing multiple pages with different content types."""
    # Arrange
    image_paths = ["/tmp/test_image1.png", "/tmp/test_image2.png", "/tmp/test_image3.png"]
    content_types = ["text", "math", "diagram"]  # Mixed content types
    
    # Setup a mock that verifies each content type is processed correctly
    def mock_process_with_content_type_check(image_path, **kwargs):
        index = image_paths.index(image_path)
        expected_content_type = content_types[index]
        
        # Verify correct content type is passed
        assert kwargs["content_type"] == expected_content_type, f"Expected {expected_content_type} but got {kwargs['content_type']}"
        
        # Return different results based on content type
        if expected_content_type == "text":
            return True, f"Text content from page {index+1}"
        elif expected_content_type == "math":
            return True, f"Math equations from page {index+1}"
        elif expected_content_type == "diagram":
            return True, f"Diagram description from page {index+1}"
    
    # Setup the test with controlled content types
    with patch.object(claude_vision_adapter_sequential, 'process_image', side_effect=mock_process_with_content_type_check) as mock_process:
        # Act
        success, result = claude_vision_adapter_sequential.process_multiple_images(
            image_paths=image_paths,
            content_types=content_types,  # Explicitly set different content types
            maintain_context=False,  # Disable context for simpler testing
        )
        
        # Assert
        assert success is True
        assert "Text content from page 1" in result
        assert "Math equations from page 2" in result
        assert "Diagram description from page 3" in result
        
        # Verify process_image was called with correct content types
        assert mock_process.call_count == 3
        for i, call_args in enumerate(mock_process.call_args_list):
            assert call_args[1]["content_type"] == content_types[i]
