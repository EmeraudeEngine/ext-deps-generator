#include <iostream>

#include "png.h"
#include "ft2build.h"
#include FT_FREETYPE_H
#include "zip.h"

int
main (int /*argc*/, char * /*argv*/[])
{
  	std::cout << "Dependencies tests." "\n";

  	{
  		int errorCode = 0;

  		auto * zip = zip_open("inexistant.zip", 0, &errorCode);

  		if ( zip != nullptr )
  		{
			zip_close(zip);
  			zip = nullptr;
  		}
  		else
  		{
  			zip_error_t error;
  			zip_error_init_with_code(&error, errorCode);

  			std::cout << "Expected error from ziplib (No such file !) : " << zip_error_strerror(&error) << " !" "\n";

  			zip_error_fini(&error);
  		}
  	}

  	{
  		/* create a png read struct. */
  		auto * png = png_create_read_struct(PNG_LIBPNG_VER_STRING, nullptr, nullptr, nullptr);

  		if ( png == nullptr )
  		{
  			return false;
  		}

  		/* create a png info struct. */
  		auto * pngInfo = png_create_info_struct(png);

  		if ( pngInfo == nullptr )
  		{
  			return false;
  		}
  	}

	FT_Library library;

	if ( FT_Init_FreeType(&library) > 0 )
	{
		std::cerr << "[ERROR] " << __PRETTY_FUNCTION__ << ", FreeType 2 init failed !" "\n";

		return EXIT_FAILURE;
	}

	FT_Done_FreeType(library);

	return EXIT_SUCCESS;
}
